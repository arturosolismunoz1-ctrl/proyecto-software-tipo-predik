"""
CLI runner for ETL pipelines.
Usage:
  python backend/scripts/run_etl.py --source inegi_denue --estado 09 --max-records 500
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.db import SessionLocal
from app.etl.denue import DenueETL

_SOURCES = {
    "inegi_denue": DenueETL,
}


async def main(source: str, estado: str, keyword: str, max_records: int, h3_resolution: int) -> None:
    etl_cls = _SOURCES.get(source)
    if etl_cls is None:
        print(f"[etl] Fuente desconocida: {source}. Opciones: {list(_SOURCES)}")
        sys.exit(1)

    print(f"[etl] Iniciando ETL para '{source}' — estado={estado}, max_records={max_records}")
    db = SessionLocal()
    try:
        etl = etl_cls()
        stats = await etl.run(db, resolution=h3_resolution, estado=estado, keyword=keyword, max_records=max_records)
        print(
            f"[etl] Completado — extraídos: {stats['extracted']}, "
            f"cargados en raw_data: {stats['loaded']}, "
            f"celdas H3 en cube: {stats['aggregated']}"
        )
    except Exception as e:
        db.rollback()
        print(f"[etl] ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecutar pipeline ETL")
    parser.add_argument("--source", default="inegi_denue", choices=list(_SOURCES))
    parser.add_argument("--estado", default="09", help="Código de entidad INEGI (09=CDMX)")
    parser.add_argument("--keyword", default="", help="Palabra clave de búsqueda")
    parser.add_argument("--max-records", type=int, default=100, dest="max_records")
    parser.add_argument("--h3-resolution", type=int, default=9, dest="h3_resolution")
    args = parser.parse_args()

    asyncio.run(main(args.source, args.estado, args.keyword, args.max_records, args.h3_resolution))
