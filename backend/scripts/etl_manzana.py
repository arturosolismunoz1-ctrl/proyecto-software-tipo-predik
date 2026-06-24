"""
ETL Manzana — carga geometrías y demografía a nivel manzana urbana.

Fuentes:
  - Geometría: data/mgn/{estado}_*.zip  →  *m.shp  (manzanas MGN 2025)
  - Demografía: data/censo_2020/RESAGEBURB_{nn}CSV20.csv  (filas MZA != 000)

Carga en: raw_data.manzana_vivienda

Uso:
  python backend/scripts/etl_manzana.py
  python backend/scripts/etl_manzana.py --estado 14
"""
import argparse
import csv
import json
import os
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import psycopg2
import shapefile
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform
from shapely.wkb import dumps as wkb_dumps

# Reproyector MGN ITRF2008 LCC (EPSG:6372) → WGS84 (EPSG:4326)
_REPROJ = Transformer.from_crs("EPSG:6372", "EPSG:4326", always_xy=True)

DATABASE_URL = os.getenv("DATABASE_URL", "")

ESTADOS = {
    "01": "01_aguascalientes",        "02": "02_bajacalifornia",
    "03": "03_bajacaliforniasur",     "04": "04_campeche",
    "05": "05_coahuiladezaragoza",    "06": "06_colima",
    "07": "07_chiapas",               "08": "08_chihuahua",
    "09": "09_ciudaddemexico",        "10": "10_durango",
    "11": "11_guanajuato",            "12": "12_guerrero",
    "13": "13_hidalgo",               "14": "14_jalisco",
    "15": "15_mexico",                "16": "16_michoacandeocampo",
    "17": "17_morelos",               "18": "18_nayarit",
    "19": "19_nuevoleon",             "20": "20_oaxaca",
    "21": "21_puebla",                "22": "22_queretaro",
    "23": "23_quintanaroo",           "24": "24_sanluispotosi",
    "25": "25_sinaloa",               "26": "26_sonora",
    "27": "27_tabasco",               "28": "28_tamaulipas",
    "29": "29_tlaxcala",              "30": "30_veracruzignaciodelallave",
    "31": "31_yucatan",               "32": "32_zacatecas",
}

# Columnas del Censo que se guardan en indicadores JSON (socioeconomicas extra)
_COLS_INDICADORES = [
    "POBTOT", "POBFEM", "POBMAS",
    "P_0A2", "P_3A5", "P_6A11", "P_12A14", "P_15A17", "P_18A24", "P_60YMAS",
    "POB0_14", "POB15_64", "POB65_MAS",
    "PEA", "POCUPADA", "PDESOCUP",
    "GRAPROES",
    "PCATOLICA", "PRO_CRIEVA", "PSIN_RELIG",
    "TOTHOG", "VIVTOT", "TVIVHAB", "VIVPAR_HAB",
    "VPH_PC", "VPH_INTER", "VPH_CEL", "VPH_AUTOM",
]


def _db_conn():
    url = DATABASE_URL.replace("postgresql+psycopg2://", "")
    user, rest = url.split(":", 1)
    pwd, rest = rest.split("@", 1)
    host_port, db = rest.rsplit("/", 1)
    if ":" in host_port:
        host, port = host_port.split(":")
    else:
        host, port = host_port, "5432"
    return psycopg2.connect(dbname=db, user=user, password=pwd, host=host, port=port)


def _leer_censo_manzana(csv_path: Path) -> dict:
    """Retorna dict {cvegeo_16: {campo: valor}} para filas de manzana (MZA != 000)."""
    datos = {}
    with open(csv_path, encoding="latin1", newline="") as f:
        reader = csv.DictReader(f)
        # Normalizar nombre BOM de la primera columna
        fields = reader.fieldnames or []
        renamed = {fields[0]: "ENTIDAD"} if fields and fields[0] != "ENTIDAD" else {}

        for row in reader:
            # Renombrar si tiene BOM
            if renamed:
                row["ENTIDAD"] = row.pop(fields[0], row.get("ENTIDAD", ""))

            mza = row.get("MZA", "").strip().zfill(3)
            if mza in ("000", ""):
                continue  # fila de AGEB o totales

            ent  = row.get("ENTIDAD", "").strip().zfill(2)
            mun  = row.get("MUN", "").strip().zfill(3)
            loc  = row.get("LOC", "").strip().zfill(4)
            ageb = row.get("AGEB", "").strip().zfill(4)
            cvegeo = ent + mun + loc + ageb + mza  # 16 chars

            def _int(v):
                try:
                    return int(v)
                except (ValueError, TypeError):
                    return None

            datos[cvegeo] = {
                "ent": ent, "mun": mun, "loc": loc, "ageb": ageb, "mza": mza,
                "vivtot":     _int(row.get("VIVTOT")),
                "vivpar":     _int(row.get("TVIVPAR")),
                "vivpar_hab": _int(row.get("VIVPAR_HAB")),
                "con_agua":   _int(row.get("VPH_AGUADV")),
                "con_dren":   _int(row.get("VPH_DRENAJ")),
                "con_luz":    _int(row.get("VPH_C_ELEC")),
                "indicadores": {
                    k: _int(row.get(k)) for k in _COLS_INDICADORES if row.get(k)
                },
            }
    return datos


def _extraer_shp_manzana(zip_path: Path, tmpdir: Path, clave: str):
    """Extrae *m.shp y companions del ZIP al tmpdir."""
    stem_target = f"{clave}m"
    companions = [".shp", ".dbf", ".prj", ".shx", ".cpg",
                  ".SHP", ".DBF", ".PRJ", ".SHX", ".CPG"]
    with zipfile.ZipFile(zip_path) as zf:
        for entry in zf.namelist():
            entry_stem = Path(entry).stem.lower()
            entry_ext  = Path(entry).suffix.lower()
            if entry_stem == stem_target and entry_ext in [e.lower() for e in companions]:
                dest = tmpdir / Path(entry).name
                with zf.open(entry) as src, open(dest, "wb") as dst:
                    dst.write(src.read())

    shps = list(tmpdir.glob(f"{stem_target}.shp")) + list(tmpdir.glob(f"{stem_target.upper()}.SHP"))
    return shps[0] if shps else None


def _cargar_estado(conn, clave: str, zip_path: Path, csv_path: Path, batch_size: int = 500) -> int:
    print(f"\n  [{clave}] {zip_path.stem}")

    # 1 — Leer demografía de Censo
    t0 = time.time()
    censo = _leer_censo_manzana(csv_path)
    print(f"      Censo: {len(censo):,} manzanas leídas ({time.time()-t0:.1f}s)")

    # 2 — Extraer shapefile
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmpdir = Path(tmp)
        shp_path = _extraer_shp_manzana(zip_path, tmpdir, clave)
        if not shp_path:
            print(f"      [SKIP] No se encontró {clave}m.shp en {zip_path.name}")
            return 0

        sf = shapefile.Reader(str(shp_path), encoding="latin1")
        fields = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag

        cur = conn.cursor()
        total = 0
        batch = []

        for rec in sf.shapeRecords():
            attrs = dict(zip(fields, rec.record))
            cvegeo = str(attrs.get("CVEGEO", "")).strip()
            if not cvegeo:
                continue

            # Geometría WKB hex — reproyectar de EPSG:6372 (LCC México) a EPSG:4326 (WGS84)
            try:
                geom_shp = rec.shape.__geo_interface__
                geom_wgs84 = shapely_transform(_REPROJ.transform, shape(geom_shp))
                geom_wkb = wkb_dumps(geom_wgs84, hex=True, srid=4326)
            except Exception:
                continue

            # Demografía del Censo
            dem = censo.get(cvegeo, {})

            # cvegeo_ageb (9 chars): ent(2) + mun(3) + ageb(4) para JOIN con ageb_demographics
            # cvegeo format: ent(0:2) + mun(2:5) + loc(5:9) + ageb(9:13) + mza(13:16)
            cvegeo_ageb = (cvegeo[0:2] + cvegeo[2:5] + cvegeo[9:13]) if len(cvegeo) >= 13 else None

            batch.append((
                cvegeo,
                str(attrs.get("CVE_ENT", "")).strip(),
                str(attrs.get("CVE_MUN", "")).strip(),
                str(attrs.get("CVE_LOC", "")).strip(),
                str(attrs.get("CVE_AGEB", "")).strip(),
                str(attrs.get("CVE_MZA", "")).strip(),
                cvegeo_ageb,
                dem.get("vivtot"),
                dem.get("vivpar"),
                dem.get("vivpar_hab"),
                dem.get("con_agua"),
                dem.get("con_dren"),
                dem.get("con_luz"),
                geom_wkb,
                json.dumps(dem.get("indicadores", {})) if dem else None,
                "MGN2025+CENSO2020",
                datetime.now(timezone.utc),
            ))

            if len(batch) >= batch_size:
                _upsert(cur, batch)
                total += len(batch)
                batch = []

        if batch:
            _upsert(cur, batch)
            total += len(batch)

        conn.commit()
        cur.close()
        print(f"      Cargadas: {total:,} manzanas ({time.time()-t0:.1f}s)")
        return total


def _upsert(cur, batch):
    cur.executemany("""
        INSERT INTO raw_data.manzana_vivienda
            (cvegeo, clave_ent, clave_mun, cve_loc, cve_ageb, cve_mza,
             cvegeo_ageb, vivtot, vivpar, vivpar_hab,
             con_agua, con_dren, con_luz,
             geom, indicadores, fuente, loaded_at)
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            ST_Multi(ST_SetSRID(ST_GeomFromWKB(decode(%s,'hex')), 4326)),
            %s::jsonb, %s, %s
        )
        ON CONFLICT (cvegeo) DO UPDATE SET
            vivtot      = EXCLUDED.vivtot,
            vivpar      = EXCLUDED.vivpar,
            vivpar_hab  = EXCLUDED.vivpar_hab,
            con_agua    = EXCLUDED.con_agua,
            con_dren    = EXCLUDED.con_dren,
            con_luz     = EXCLUDED.con_luz,
            geom        = EXCLUDED.geom,
            indicadores = EXCLUDED.indicadores,
            loaded_at   = EXCLUDED.loaded_at
    """, batch)


def main():
    parser = argparse.ArgumentParser(description="ETL Manzana — MGN + Censo 2020")
    parser.add_argument("--estado", default=None, help="Clave de estado (ej. 14). Omitir = todos")
    args = parser.parse_args()

    base_dir  = Path(__file__).resolve().parents[2]
    mgn_dir   = base_dir / "data" / "mgn"
    censo_dir = base_dir / "data" / "censo_2020"

    estados = {args.estado.zfill(2): ESTADOS[args.estado.zfill(2)]} if args.estado else ESTADOS

    print("\n" + "=" * 65)
    print("  ETL MANZANA — MGN 2025 + Censo 2020")
    print(f"  Estados: {len(estados)}")
    print(f"  Inicio:  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)

    conn = _db_conn()
    # cvegeo es PK — ON CONFLICT funciona sin constraint adicional
    total_global = 0
    errores = []

    for clave in sorted(estados.keys()):
        zip_name = estados[clave] + ".zip"
        zip_path = mgn_dir / zip_name
        csv_path = censo_dir / f"RESAGEBURB_{clave}CSV20.csv"

        if not zip_path.exists():
            print(f"  [{clave}] SKIP — no existe {zip_path.name}")
            errores.append(clave)
            continue
        if not csv_path.exists():
            print(f"  [{clave}] SKIP — no existe {csv_path.name}")
            errores.append(clave)
            continue

        try:
            n = _cargar_estado(conn, clave, zip_path, csv_path)
            total_global += n
        except Exception as e:
            print(f"  [{clave}] ERROR: {e}")
            conn.rollback()
            errores.append(clave)

    conn.close()

    print("\n" + "=" * 65)
    print(f"  COMPLETADO: {total_global:,} manzanas cargadas")
    if errores:
        print(f"  Estados con error: {errores}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
