"""
Carga el shapefile de AGEBs del Marco Geoestadístico Nacional (MGN) de INEGI
hacia la tabla raw_data.ageb_geometries.

Descarga el MGN en:
  https://www.inegi.org.mx/temas/mg/default.html#Descargas
  → Edición 2025 → Por entidad o Nacional → descomprimir el ZIP.

El shapefile de AGEBs urbanas suele llamarse:
  <clave_entidad>a.shp   (ej. 09a.shp para CDMX)
  00a.shp                (nacional — todos los estados)

Uso:
  # ZIP integrado nacional (recomendado — carga los 32 estados de una vez)
  python backend/scripts/load_marco_geoestadistico.py --zip data/mgn/mg_2025_integrado.zip

  # Directorio con ZIPs por estado (01_aguascalientes.zip ... 32_zacatecas.zip)
  python backend/scripts/load_marco_geoestadistico.py --zip-dir data/mgn/

  # Shapefile ya extraído
  python backend/scripts/load_marco_geoestadistico.py --shapefile data/mgn/00a.shp

  # Directorio ya extraído (busca *a.shp)
  python backend/scripts/load_marco_geoestadistico.py --dir data/mgn/
"""
import argparse
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import shapefile as pyshp
from pyproj import Transformer
from shapely.geometry import shape as shapely_shape, mapping
from shapely.geometry import MultiPolygon
from shapely.ops import transform as shapely_transform
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Reproyector de LCC México ITRF2008 (EPSG:6372) a WGS84 (EPSG:4326)
_REPROJ = Transformer.from_crs("EPSG:6372", "EPSG:4326", always_xy=True)

from app.db import SessionLocal
from app.models.raw_data import AgebGeometry

# ── Mapeo de campos del shapefile del MGN ─────────────────────────────────────
_FIELD_ALIASES = {
    "cvegeo":    ["CVEGEO", "CLAVE", "CVE_GEO"],
    "clave_ent": ["CLAVE_ENT", "CVE_ENT", "ENTIDAD"],
    "clave_mun": ["CLAVE_MUN", "CVE_MUN", "MUN"],
    "cve_loc":   ["CVE_LOC", "LOC"],
    "cve_ageb":  ["CVE_AGEB", "AGEB"],
    "nom_ent":   ["NOM_ENT", "NOM_ENTIDAD", "NOMGEO"],
    "nom_mun":   ["NOM_MUN", "NOM_MUNICIPIO"],
    "nom_loc":   ["NOM_LOC", "NOM_LOCALIDAD"],
    "ambito":    ["AMBITO", "TIPOLOGIA"],
}

_ENCODINGS_TO_TRY = ["utf-8", "latin-1", "cp1252"]


def _resolve_fields(field_names: list[str]) -> dict[str, str | None]:
    available = {f.upper() for f in field_names}
    resolved = {}
    for our_name, aliases in _FIELD_ALIASES.items():
        match = next((a for a in aliases if a in available), None)
        resolved[our_name] = match
    return resolved


def _get_val(record: dict, field: str | None, default="") -> str:
    if field is None:
        return default
    return str(record.get(field, "") or "").strip()


def _read_cpg(cpg_path: Path) -> Optional[str]:
    try:
        enc = cpg_path.read_text(errors="ignore").strip()
        if enc:
            return enc
    except Exception:
        pass
    return None


def _shape_to_wkt_multipolygon(shp) -> str | None:
    try:
        geojson = shp.__geo_interface__
        geom = shapely_shape(geojson)
        if geom.geom_type == "Polygon":
            geom = MultiPolygon([geom])
        if geom.is_empty or not geom.is_valid:
            geom = geom.buffer(0)
        # Reproyectar de LCC México (EPSG:6372) a WGS84 (EPSG:4326)
        geom = shapely_transform(_REPROJ.transform, geom)
        return geom.wkt
    except Exception:
        return None


def _open_reader(shp_path: Path) -> pyshp.Reader:
    """Intenta abrir el shapefile con distintos encodings."""
    cpg_path = shp_path.with_suffix(".cpg")
    if not cpg_path.exists():
        cpg_path = shp_path.parent / (shp_path.stem + ".CPG")

    cpg_enc = _read_cpg(cpg_path) if cpg_path.exists() else None
    encs = ([cpg_enc] if cpg_enc else []) + [e for e in _ENCODINGS_TO_TRY if e != cpg_enc]

    for enc in encs:
        try:
            reader = pyshp.Reader(str(shp_path), encoding=enc)
            # Force-read one record to validate encoding
            _ = reader.records()[0] if reader.numRecords else None
            return reader
        except Exception:
            continue

    raise RuntimeError(f"No se pudo abrir {shp_path} con ningún encoding")


# ── Carga de un shapefile ya extraído ─────────────────────────────────────────

def load_shapefile(path: str, batch_size: int = 500, entidad_filter: str | None = None) -> int:
    shp_path = Path(path)
    try:
        reader = _open_reader(shp_path)
    except RuntimeError as e:
        print(f"[mgn] ERROR abriendo shapefile: {e}")
        return 0

    try:
        field_names = [f[0] for f in reader.fields[1:]]
        field_map = _resolve_fields(field_names)

        print(f"[mgn] Campos detectados: {field_names}")
        print(f"[mgn] Mapeo → {field_map}")
        print(f"[mgn] Registros totales: {reader.numRecords:,}")

        db = SessionLocal()
        total = 0
        batch = []

        try:
            for sr in reader.shapeRecords():
                rec = dict(zip(field_names, sr.record))

                clave_ent = _get_val(rec, field_map.get("clave_ent"))
                if entidad_filter and clave_ent != entidad_filter:
                    continue

                wkt = _shape_to_wkt_multipolygon(sr.shape)
                if wkt is None:
                    continue

                cvegeo = _get_val(rec, field_map.get("cvegeo"))
                if not cvegeo:
                    mun  = _get_val(rec, field_map.get("clave_mun")).zfill(3)
                    loc  = _get_val(rec, field_map.get("cve_loc")).zfill(4)
                    ageb = _get_val(rec, field_map.get("cve_ageb"))
                    cvegeo = clave_ent.zfill(2) + mun + loc + ageb

                if not cvegeo or len(cvegeo) < 8:
                    continue

                clave_mun = _get_val(rec, field_map.get("clave_mun"))
                cve_ageb  = _get_val(rec, field_map.get("cve_ageb"))
                cvegeo_9  = (
                    clave_ent.zfill(2) + clave_mun.zfill(3) + cve_ageb.zfill(4)
                    if clave_ent and clave_mun and cve_ageb else None
                )

                batch.append({
                    "cvegeo":    cvegeo,
                    "clave_ent": clave_ent,
                    "clave_mun": clave_mun,
                    "cve_loc":   _get_val(rec, field_map.get("cve_loc")),
                    "cve_ageb":  cve_ageb,
                    "cvegeo_9":  cvegeo_9,
                    "nom_ent":   _get_val(rec, field_map.get("nom_ent")),
                    "nom_mun":   _get_val(rec, field_map.get("nom_mun")),
                    "nom_loc":   _get_val(rec, field_map.get("nom_loc")),
                    "ambito":    _get_val(rec, field_map.get("ambito"), "Urbana"),
                    "geom":      f"SRID=4326;{wkt}",
                    "loaded_at": datetime.now(timezone.utc),
                })

                if len(batch) >= batch_size:
                    _flush(db, batch)
                    total += len(batch)
                    if total % 5000 == 0:
                        print(f"[mgn]   {total:,} AGEBs cargadas...")
                    batch.clear()

            if batch:
                _flush(db, batch)
                total += len(batch)

            db.commit()
            print(f"[mgn] ✓ {total:,} AGEBs cargadas desde {shp_path.name}")
            return total

        except Exception as e:
            db.rollback()
            print(f"[mgn] ERROR: {e}")
            raise
        finally:
            db.close()

    finally:
        # Cierra explícitamente el reader para liberar handles de archivo (necesario en Windows)
        try:
            reader.close()
        except Exception:
            pass


def _flush(db, batch: list) -> None:
    stmt = pg_insert(AgebGeometry).values(batch)
    stmt = stmt.on_conflict_do_update(
        index_elements=["cvegeo"],
        set_={
            "geom":      stmt.excluded.geom,
            "cvegeo_9":  stmt.excluded.cvegeo_9,
            "nom_ent":   stmt.excluded.nom_ent,
            "nom_mun":   stmt.excluded.nom_mun,
            "nom_loc":   stmt.excluded.nom_loc,
            "ambito":    stmt.excluded.ambito,
            "loaded_at": stmt.excluded.loaded_at,
        },
    )
    db.execute(stmt)


# ── Carga desde un ZIP (extrae a temp y carga) ────────────────────────────────

def _extraer_ageb_shapefiles_de_zip(zip_path: Path, tmpdir: Path) -> List[Path]:
    """
    Extrae los shapefiles de AGEBs urbanas del ZIP a tmpdir.
    Patrón: *a.shp (excluye *ar.shp, *mun.shp, etc.)
    """
    companions = [".shp", ".dbf", ".prj", ".shx", ".cpg",
                  ".SHP", ".DBF", ".PRJ", ".SHX", ".CPG"]
    shp_extraidos = []

    with zipfile.ZipFile(zip_path) as zf:
        nombres = zf.namelist()
        # Identificar shapefiles AGEB
        candidatos = [
            n for n in nombres
            if n.lower().endswith(".shp")
            and Path(n).stem.lower().endswith("a")
            and not Path(n).stem.lower().endswith("ra")
            and not any(Path(n).stem.lower().endswith(x)
                        for x in ["mun", "ent", "mza", "loc", "red", "sia", "sil", "sip",
                                   "lpr", "cd", "fm", "ti", "pe", "pem"])
        ]

        if not candidatos:
            print(f"[mgn]   No se encontró shapefile de AGEBs en {zip_path.name}")
            return []

        for shp_entry in candidatos:
            base_dir = str(Path(shp_entry).parent)
            base_name = Path(shp_entry).stem

            for ext in companions:
                entry = f"{base_dir}/{base_name}{ext}" if base_dir != "." else f"{base_name}{ext}"
                if entry in nombres:
                    dest = tmpdir / Path(entry).name
                    with zf.open(entry) as src, open(dest, "wb") as dst:
                        dst.write(src.read())

            extracted = tmpdir / f"{base_name}.shp"
            if extracted.exists():
                shp_extraidos.append(extracted)

    return shp_extraidos


def load_from_zip(zip_path: str, batch_size: int = 500, entidad_filter: str | None = None) -> int:
    """Extrae el shapefile de AGEBs del ZIP a una carpeta temporal y lo carga."""
    zip_path = Path(zip_path)
    print(f"\n[mgn] Procesando ZIP: {zip_path.name} ...")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        shapefiles = _extraer_ageb_shapefiles_de_zip(zip_path, Path(tmpdir))
        if not shapefiles:
            return 0

        total = 0
        for shp in shapefiles:
            total += load_shapefile(str(shp), batch_size=batch_size,
                                    entidad_filter=entidad_filter)
        return total


def load_all_zips(directorio: str, batch_size: int = 500, skip_integrado: bool = True) -> int:
    """
    Procesa todos los ZIPs de estados en el directorio.
    Ordena por nombre para garantizar secuencia 01→32.
    """
    root = Path(directorio)
    zips = sorted(root.glob("*.zip"))

    if skip_integrado:
        zips = [z for z in zips if "integrado" not in z.stem]

    if not zips:
        print(f"[mgn] No se encontraron ZIPs en: {directorio}")
        return 0

    print(f"[mgn] Procesando {len(zips)} ZIPs de estados...")
    total = 0
    for i, zip_path in enumerate(zips, 1):
        print(f"\n[mgn] ── Estado {i}/{len(zips)}: {zip_path.name} ──")
        total += load_from_zip(str(zip_path), batch_size=batch_size)
        print(f"[mgn] Acumulado: {total:,} AGEBs")

    print(f"\n[mgn] TOTAL NACIONAL: {total:,} AGEBs cargadas en raw_data.ageb_geometries")
    return total


# ── Auto-descubrimiento en directorio (ya extraído) ───────────────────────────

def _encontrar_shapefiles_ageb(directorio: str) -> List[str]:
    root = Path(directorio)
    candidatos = []
    for shp in root.rglob("*.shp"):
        nombre = shp.stem.lower()
        if (nombre.endswith("a")
                and not nombre.endswith("ra")
                and not any(nombre.endswith(s)
                            for s in ["mun", "ent", "mza", "loc", "red", "sia", "sil", "sip",
                                      "lpr", "cd", "fm", "ti", "pe", "pem"])):
            candidatos.append(str(shp))
    return sorted(candidatos)


def load_directory(directorio: str, batch_size: int = 500) -> int:
    shapefiles = _encontrar_shapefiles_ageb(directorio)
    if not shapefiles:
        print(f"[mgn] No se encontraron shapefiles de AGEBs en: {directorio}")
        return 0

    print(f"[mgn] Encontrados {len(shapefiles)} shapefile(s):")
    for s in shapefiles:
        print(f"  {s}")

    total = 0
    for shp_path in shapefiles:
        print(f"\n[mgn] Procesando: {Path(shp_path).name}")
        total += load_shapefile(shp_path, batch_size=batch_size)

    print(f"\n[mgn] TOTAL: {total:,} AGEBs cargadas en raw_data.ageb_geometries")
    return total


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga MGN shapefile de AGEBs → PostgreSQL")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--zip",      help="ZIP específico (ej. data/mgn/mg_2025_integrado.zip)")
    group.add_argument("--zip-dir",  help="Directorio con ZIPs por estado — procesa todos")
    group.add_argument("--shapefile",help="Ruta a un .shp ya extraído (ej. data/mgn/00a.shp)")
    group.add_argument("--dir",      help="Directorio ya extraído — auto-descubre *a.shp")
    parser.add_argument("--batch",   type=int, default=500)
    parser.add_argument("--entidad", default=None, help="Filtrar por entidad (ej. 09). Solo con --zip o --shapefile")
    args = parser.parse_args()

    if args.zip:
        load_from_zip(args.zip, batch_size=args.batch, entidad_filter=args.entidad)
    elif args.zip_dir:
        load_all_zips(args.zip_dir, batch_size=args.batch)
    elif args.shapefile:
        if not os.path.exists(args.shapefile):
            print(f"ERROR: No se encuentra: {args.shapefile}")
            sys.exit(1)
        load_shapefile(args.shapefile, batch_size=args.batch, entidad_filter=args.entidad)
    else:
        if not os.path.isdir(args.dir):
            print(f"ERROR: No es un directorio: {args.dir}")
            sys.exit(1)
        load_directory(args.dir, batch_size=args.batch)
