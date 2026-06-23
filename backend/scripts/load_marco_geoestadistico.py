"""
Carga el shapefile de AGEBs del Marco Geoestadístico Nacional (MGN) de INEGI
hacia la tabla raw_data.ageb_geometries.

Descarga el MGN en:
  https://www.inegi.org.mx/temas/mg/default.html#Descargas
  → Edición 2020 → Por entidad o Nacional → descomprimir el ZIP.

El shapefile de AGEBs urbanas suele llamarse:
  <clave_entidad>a.shp   (ej. 09a.shp para CDMX)
  00a.shp                (nacional)

Uso:
  python backend/scripts/load_marco_geoestadistico.py --shapefile data/mgn/09a.shp
  python backend/scripts/load_marco_geoestadistico.py --shapefile data/mgn/00a.shp --batch 500
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import shapefile as pyshp
from shapely.geometry import shape as shapely_shape, mapping
from shapely.ops import unary_union
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models.raw_data import AgebGeometry

# ── Mapeo de campos del shapefile del MGN ─────────────────────────────────────
# INEGI puede usar distintos nombres según la edición; se prueban variantes.
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


def _resolve_fields(field_names: list[str]) -> dict[str, str | None]:
    """Devuelve un dict {campo_nuestro: campo_en_shapefile | None}."""
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


def _shape_to_wkt_multipolygon(shp) -> str | None:
    """Convierte una shape de pyshp a WKT MULTIPOLYGON usando shapely."""
    try:
        geojson = shp.__geo_interface__
        geom = shapely_shape(geojson)
        # Normalizar siempre a MultiPolygon
        if geom.geom_type == "Polygon":
            from shapely.geometry import MultiPolygon
            geom = MultiPolygon([geom])
        if geom.is_empty or not geom.is_valid:
            geom = geom.buffer(0)
        return geom.wkt
    except Exception:
        return None


def load_shapefile(path: str, batch_size: int = 500, entidad_filter: str | None = None) -> int:
    reader = pyshp.Reader(path, encoding="utf-8")
    field_names = [f[0] for f in reader.fields[1:]]  # skip DeletionFlag
    field_map = _resolve_fields(field_names)

    print(f"[mgn] Campos detectados en shapefile: {field_names}")
    print(f"[mgn] Mapeo → {field_map}")

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

            # Construir cvegeo si no viene directamente del shapefile
            cvegeo = _get_val(rec, field_map.get("cvegeo"))
            if not cvegeo:
                mun = _get_val(rec, field_map.get("clave_mun")).zfill(3)
                loc = _get_val(rec, field_map.get("cve_loc")).zfill(4)
                ageb = _get_val(rec, field_map.get("cve_ageb"))
                cvegeo = clave_ent.zfill(2) + mun + loc + ageb

            if not cvegeo or len(cvegeo) < 8:
                continue

            batch.append({
                "cvegeo":    cvegeo,
                "clave_ent": clave_ent,
                "clave_mun": _get_val(rec, field_map.get("clave_mun")),
                "cve_loc":   _get_val(rec, field_map.get("cve_loc")),
                "cve_ageb":  _get_val(rec, field_map.get("cve_ageb")),
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
                print(f"[mgn] {total} AGEBs cargados...")
                batch.clear()

        if batch:
            _flush(db, batch)
            total += len(batch)

        db.commit()
        print(f"[mgn] ✓ Carga completa: {total} AGEBs en raw_data.ageb_geometries")
        return total

    except Exception as e:
        db.rollback()
        print(f"[mgn] ERROR: {e}")
        raise
    finally:
        db.close()


def _flush(db, batch: list) -> None:
    stmt = pg_insert(AgebGeometry).values(batch)
    stmt = stmt.on_conflict_do_update(
        index_elements=["cvegeo"],
        set_={
            "geom":      stmt.excluded.geom,
            "nom_ent":   stmt.excluded.nom_ent,
            "nom_mun":   stmt.excluded.nom_mun,
            "nom_loc":   stmt.excluded.nom_loc,
            "ambito":    stmt.excluded.ambito,
            "loaded_at": stmt.excluded.loaded_at,
        },
    )
    db.execute(stmt)


def _encontrar_shapefiles_ageb(directorio: str) -> List[str]:
    """
    Auto-descubre shapefiles de AGEBs urbanas en una carpeta MGN.
    Patrones conocidos:
      - 00a.shp / 09a.shp  (MGN 2020/2023/2025 nacional y por estado)
      - conjunto_de_datos/00a.shp  (estructura ZIP nacional)
    Excluye: *ra.shp (rurales), *mun.shp, *ent.shp, *mza.shp
    """
    root = Path(directorio)
    candidatos = []
    for shp in root.rglob("*.shp"):
        nombre = shp.stem.lower()
        # Incluir solo los que terminan en 'a' (AGEBs urbanas)
        # Excluir rurales (ra), municipios (mun), entidades (ent), manzanas (mza)
        if (nombre.endswith("a")
                and not nombre.endswith("ra")
                and not any(nombre.endswith(s) for s in ["mun","ent","mza","loc","red"])):
            candidatos.append(str(shp))
    return sorted(candidatos)


def load_directory(directorio: str, batch_size: int = 500) -> int:
    """Carga todos los shapefiles de AGEBs urbanas encontrados en el directorio."""
    shapefiles = _encontrar_shapefiles_ageb(directorio)
    if not shapefiles:
        print(f"[mgn] No se encontraron shapefiles de AGEBs en: {directorio}")
        print("[mgn] Estructura esperada: *a.shp (ej. 00a.shp, 09a.shp)")
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga MGN shapefile de AGEBs -> PostgreSQL")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--shapefile", help="Ruta a un .shp especifico (ej. data/mgn/09a.shp)")
    group.add_argument("--dir", help="Directorio MGN — auto-descubre todos los *a.shp")
    parser.add_argument("--batch", type=int, default=500, help="Batch de insercion (default: 500)")
    parser.add_argument("--entidad", default=None, help="Filtra entidad (ej. 09). Solo con --shapefile")
    args = parser.parse_args()

    if args.shapefile:
        if not os.path.exists(args.shapefile):
            print(f"ERROR: No se encuentra: {args.shapefile}")
            sys.exit(1)
        load_shapefile(args.shapefile, batch_size=args.batch, entidad_filter=args.entidad)
    else:
        if not os.path.isdir(args.dir):
            print(f"ERROR: No es un directorio: {args.dir}")
            sys.exit(1)
        load_directory(args.dir, batch_size=args.batch)
