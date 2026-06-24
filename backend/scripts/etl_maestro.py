"""
ETL Maestro — pobla la base de datos completa de Predik Geo.

Orquesta tres fuentes:
  1. Marco Geoestadistico Nacional (MGN) -> ageb_geometries, manzana_vivienda
  2. Censo de Poblacion 2020             -> ageb_demographics
  3. DENUE via API (paginado)            -> denue_establishments (todos los estados)

Uso:
  python backend/scripts/etl_maestro.py --todo
  python backend/scripts/etl_maestro.py --solo-denue
  python backend/scripts/etl_maestro.py --solo-denue --estados 09,14,15
  python backend/scripts/etl_maestro.py --solo-geo
  python backend/scripts/etl_maestro.py --solo-censo
"""
import argparse
import asyncio
import json
import os
import sys
import time
import urllib.request as _urllib
from datetime import datetime
from pathlib import Path

# Forzar stdout sin buffer para que logs aparezcan en tiempo real
sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal

# ── Catalogo de estados ────────────────────────────────────────────────────────

ESTADOS = {
    "01": "Aguascalientes",    "02": "Baja California",
    "03": "Baja California Sur","04": "Campeche",
    "05": "Coahuila",          "06": "Colima",
    "07": "Chiapas",           "08": "Chihuahua",
    "09": "Ciudad de Mexico",  "10": "Durango",
    "11": "Guanajuato",        "12": "Guerrero",
    "13": "Hidalgo",           "14": "Jalisco",
    "15": "Mexico",            "16": "Michoacan",
    "17": "Morelos",           "18": "Nayarit",
    "19": "Nuevo Leon",        "20": "Oaxaca",
    "21": "Puebla",            "22": "Queretaro",
    "23": "Quintana Roo",      "24": "San Luis Potosi",
    "25": "Sinaloa",           "26": "Sonora",
    "27": "Tabasco",           "28": "Tamaulipas",
    "29": "Tlaxcala",          "30": "Veracruz",
    "31": "Yucatan",           "32": "Zacatecas",
}

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


# ── 1. ETL Geografico (MGN) ────────────────────────────────────────────────────

def etl_marco_geoestadistico(estados_filter=None):
    """Carga shapefiles MGN desde data/mgn/ a ageb_geometries."""
    mgn_dir = DATA_DIR / "mgn"

    # Buscar shapefiles disponibles
    shapefiles = list(mgn_dir.rglob("*.shp"))
    ageb_shps = [f for f in shapefiles if f.stem.endswith("a") and not f.stem.endswith("ra")]

    if not ageb_shps:
        print("  [!] No se encontraron shapefiles de AGEBs en data/mgn/")
        print("      Descarga el MGN segun data/DESCARGAR_DATOS.md")
        return 0

    total = 0
    for shp in sorted(ageb_shps):
        estado_code = shp.stem[:2] if shp.stem[:2].isdigit() else None
        if estados_filter and estado_code not in estados_filter:
            continue
        nombre_estado = ESTADOS.get(estado_code, shp.stem)
        print(f"    Cargando AGEBs: {shp.name} ({nombre_estado})...")

        # Reutilizar script existente con parametro de archivo
        from backend.scripts.load_marco_geoestadistico import load_shapefile
        db = SessionLocal()
        try:
            n = load_shapefile(db, str(shp))
            print(f"    [OK] {n} AGEBs cargadas")
            total += n
        except Exception as e:
            print(f"    [!] Error: {e}")
        finally:
            db.close()

    return total


# ── 2. ETL Censo 2020 ──────────────────────────────────────────────────────────

def etl_censo_2020(estados_filter=None):
    """Carga CSVs del Censo 2020 desde data/censo_2020/ a ageb_demographics."""
    censo_dir = DATA_DIR / "censo_2020"
    csvs = list(censo_dir.rglob("RESAGEBURB_*.csv"))

    if not csvs:
        print("  [!] No se encontraron CSVs de Censo 2020 en data/censo_2020/")
        print("      Descarga segun data/DESCARGAR_DATOS.md")
        return 0

    total = 0
    for csv_path in sorted(csvs):
        # Extraer clave de estado del nombre: RESAGEBURB_15B_2020.csv -> 15
        parts = csv_path.stem.split("_")
        estado_code = parts[1][:2] if len(parts) > 1 else None
        if estados_filter and estado_code not in estados_filter:
            continue
        nombre_estado = ESTADOS.get(estado_code, csv_path.stem)
        print(f"    Cargando Censo: {csv_path.name} ({nombre_estado})...")

        from backend.scripts.load_censo_2020 import load_csv
        db = SessionLocal()
        try:
            n = load_csv(db, str(csv_path))
            print(f"    [OK] {n} AGEBs demograficas cargadas")
            total += n
        except Exception as e:
            print(f"    [!] Error: {e}")
        finally:
            db.close()

    return total


# ── 3. ETL DENUE paginado ──────────────────────────────────────────────────────

PAGE_SIZE = 2500  # maximo de la API INEGI DENUE

# Categorias SCIAN que cubren ~95% de todos los establecimientos DENUE.
# La API no soporta wildcard, asi que iteramos por sector.
SECTORES_DENUE = [
    "comercio",       # 43,46 – tiendas, abarrotes, farmacias, ropa, etc.
    "restaurante",    # 722 – comida y bebida
    "alimentos",      # industria alimentaria y tiendas de abarrotes
    "servicio",       # 54,56,81 – servicios profesionales, apoyo a negocios
    "salud",          # 62 – clinicas, hospitales, dentistas
    "educacion",      # 61 – escuelas, academias
    "transporte",     # 48,49 – agencias, mensajeria
    "construccion",   # 23 – materiales y contratistas
    "manufactura",    # 31-33 – industria
    "inmobiliario",   # 53 – bienes raices
    "hotel",          # 721 – hospedaje
    "banco",          # 52 – servicios financieros
    "recreacion",     # 71 – entretenimiento, deportes
    "tecnologia",     # 51 – telecomunicaciones, TI
    "agropecuario",   # 11 – campo, ganaderia
    "taller",         # 811 – reparacion autos, electrodomesticos
    "belleza",        # 812 – peluquerias, spas
    "gasolinera",     # 447 – estaciones de combustible
    "farmacia",       # 4611 – farmacias (subconjunto de comercio)
    "medico",         # medicos independientes
]


def _denue_get(url: str) -> list:
    """
    Hace GET a la API INEGI DENUE y devuelve la lista JSON.
    Retorna [] si la respuesta no es una lista valida o hay error HTTP.
    """
    req_obj = _urllib.Request(url, headers={"User-Agent": "predik-geo/1.0"})
    try:
        raw = _urllib.urlopen(req_obj, timeout=30).read()
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def _paginar_sector(
    token: str, sector: str, estado: str, etl, db
) -> tuple[int, int, int]:
    """
    Pagina un sector/keyword para un estado y carga los registros.
    Retorna (extraidos, cargados, paginas).
    """
    from app.connectors.inegi.denue import _BASE_URL, _item_to_geo_feature

    total_ext = total_carg = pagina = 0

    while True:
        inicio = pagina * PAGE_SIZE
        fin = inicio + PAGE_SIZE
        url = f"{_BASE_URL}/BuscarEntidad/{sector}/{estado}/{inicio}/{fin}/{token}"

        data = await asyncio.to_thread(_denue_get, url)
        if not data:
            break

        features = [f for item in data if (f := _item_to_geo_feature(item)) is not None]
        if features:
            total_carg += etl.load_raw(features, db)
            total_ext += len(features)

        pagina += 1
        if len(data) < PAGE_SIZE:
            break

        await asyncio.sleep(0.3)

    return total_ext, total_carg, pagina


async def descargar_estado_denue(
    estado: str,
    nombre_estado: str,
    h3_resolution: int = 9,
    sectores: list | None = None,
) -> dict:
    """
    Descarga establecimientos de un estado iterando sobre los sectores SCIAN principales.

    La API INEGI DENUE no soporta wildcard '.' (los clientes HTTP normalizan /./
    segun RFC). En su lugar iteramos por categoria, cubriendo ~95% de los giros.
    load_raw() hace ON CONFLICT DO UPDATE por CLEE, asi que duplicados entre
    sectores quedan resueltos automaticamente.
    """
    from app.etl.denue import DenueETL
    from app.connectors.inegi.denue import _BASE_URL

    token = os.getenv("INEGI_DENUE_TOKEN")
    if not token:
        print(f"    [!] INEGI_DENUE_TOKEN no configurado — omitiendo {nombre_estado}")
        return {"estado": estado, "nombre": nombre_estado, "extraidos": 0, "cargados": 0, "paginas": 0}

    sectores_a_usar = sectores or SECTORES_DENUE
    db = SessionLocal()
    etl = DenueETL()

    total_extraidos = 0
    total_cargados = 0
    total_paginas = 0

    try:
        for i, sector in enumerate(sectores_a_usar, 1):
            ext, carg, pags = await _paginar_sector(token, sector, estado, etl, db)
            total_extraidos += ext
            total_cargados += carg
            total_paginas += pags
            if ext > 0:
                print(f"      [{i:02}/{len(sectores_a_usar)}] {sector:<15} "
                      f"{ext:>6} registros | {pags} pags")

        if total_cargados > 0:
            print(f"    [OK] {nombre_estado}: {total_extraidos:,} establecimientos | "
                  f"{total_paginas} paginas")
        else:
            print(f"    [-] {nombre_estado}: 0 establecimientos nuevos")

        return {
            "estado": estado,
            "nombre": nombre_estado,
            "extraidos": total_extraidos,
            "cargados": total_cargados,
            "paginas": total_paginas,
        }

    finally:
        db.close()


async def etl_denue_todos_estados(
    estados_filter=None,
    h3_resolution: int = 9,
):
    """Ejecuta descarga paginada de DENUE para todos (o subset) de estados."""
    estados_a_procesar = {
        k: v for k, v in ESTADOS.items()
        if not estados_filter or k in estados_filter
    }

    print(f"  Procesando {len(estados_a_procesar)} estados...")
    resumen = []
    total_general = 0

    for clave, nombre in sorted(estados_a_procesar.items()):
        print(f"\n  [{clave}] {nombre}")
        t0 = time.time()
        resultado = await descargar_estado_denue(clave, nombre, h3_resolution)
        elapsed = time.time() - t0
        resultado["segundos"] = round(elapsed, 1)
        resumen.append(resultado)
        total_general += resultado["extraidos"]
        print(f"      Tiempo: {elapsed:.0f}s")

    return resumen, total_general


# ── Main ───────────────────────────────────────────────────────────────────────

def imprimir_resumen(label, n, t):
    print(f"\n  {label}: {n:,} registros en {t:.0f}s")


async def main_async():
    parser = argparse.ArgumentParser(description="ETL Maestro Predik Geo")
    parser.add_argument("--todo",         action="store_true", help="Ejecutar todo (geo + censo + denue)")
    parser.add_argument("--solo-denue",   action="store_true", help="Solo DENUE (via API)")
    parser.add_argument("--solo-geo",     action="store_true", help="Solo Marco Geoestadistico")
    parser.add_argument("--solo-censo",   action="store_true", help="Solo Censo 2020")
    parser.add_argument("--estados",      type=str,            help="Claves de estados separadas por coma. Ej: 09,14,15")
    parser.add_argument("--h3-res",       type=int, default=9, help="Resolucion H3 (default: 9)")
    args = parser.parse_args()

    estados_filter = None
    if args.estados:
        estados_filter = {e.strip().zfill(2) for e in args.estados.split(",")}

    if not any([args.todo, args.solo_denue, args.solo_geo, args.solo_censo]):
        parser.print_help()
        return

    print("\n" + "=" * 65)
    print("  ETL MAESTRO — Predik Geo")
    print(f"  Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if estados_filter:
        nombres = [ESTADOS.get(e, e) for e in sorted(estados_filter)]
        print(f"  Estados: {', '.join(nombres)}")
    else:
        print("  Estados: TODOS (32)")
    print("=" * 65)

    # ── 1. Marco Geoestadistico ───────────────────────────────────────────────
    if args.todo or args.solo_geo:
        print("\n[1/3] Marco Geoestadistico Nacional (AGEBs)...")
        t0 = time.time()
        n = etl_marco_geoestadistico(estados_filter)
        imprimir_resumen("AGEBs cargadas", n, time.time() - t0)

    # ── 2. Censo 2020 ─────────────────────────────────────────────────────────
    if args.todo or args.solo_censo:
        print("\n[2/3] Censo de Poblacion y Vivienda 2020...")
        t0 = time.time()
        n = etl_censo_2020(estados_filter)
        imprimir_resumen("AGEBs demograficas cargadas", n, time.time() - t0)

    # ── 3. DENUE ──────────────────────────────────────────────────────────────
    if args.todo or args.solo_denue:
        print("\n[3/3] DENUE — Directorio Nacional de Unidades Economicas...")
        print("  (paginado de 2,500 en 2,500 via API INEGI)")
        t0 = time.time()
        resumen, total = await etl_denue_todos_estados(estados_filter, args.h3_res)
        elapsed = time.time() - t0

        print("\n" + "-" * 65)
        print("  RESUMEN DENUE")
        print(f"  {'Estado':<30} {'Establ.':>10} {'Paginas':>8} {'Seg.':>6}")
        print("-" * 65)
        for r in resumen:
            if r["extraidos"] > 0:
                print(f"  {r.get('nombre',''):<30} {r['extraidos']:>10,} {r['paginas']:>8} {r['segundos']:>6.0f}s")
        print("-" * 65)
        print(f"  TOTAL: {total:,} establecimientos en {elapsed:.0f}s ({elapsed/60:.1f} min)")

    print("\n" + "=" * 65)
    print(f"  ETL MAESTRO completado: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65 + "\n")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
