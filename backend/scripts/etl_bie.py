"""
ETL BIE — Banco de Información Económica (INEGI)

Descarga indicadores macroeconómicos para los 32 estados y los carga en
raw_data.bie_indicadores.

Requiere: INEGI_BIE_API_TOKEN en .env
Obtener token en: https://www.inegi.org.mx/servicios/api_indicadores.html

Uso:
  # Cargar todos los estados (2020-2024)
  python backend/scripts/etl_bie.py

  # Solo un estado
  python backend/scripts/etl_bie.py --estado 14

  # Rango de fechas personalizado
  python backend/scripts/etl_bie.py --inicio 2018/01 --fin 2024/12

  # Ver datos sin cargar (dry-run)
  python backend/scripts/etl_bie.py --dry-run
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import os

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


def main():
    parser = argparse.ArgumentParser(description="ETL BIE — INEGI Indicadores Económicos")
    parser.add_argument("--estado",  default=None, help="Clave de estado a cargar (ej. 14). Omitir = todos")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra que se cargaria, sin insertar")
    args = parser.parse_args()

    token = os.getenv("INEGI_BIE_API_TOKEN", "")
    if not token:
        print("\n" + "=" * 60)
        print("  ERROR: INEGI_BIE_API_TOKEN no configurado en .env")
        print()
        print("  Pasos para obtener el token (gratis):")
        print("  1. Ir a https://www.inegi.org.mx/servicios/api_indicadores.html")
        print("  2. Hacer clic en 'Registrate'")
        print("  3. Completar el formulario con tu correo")
        print("  4. El token llega por correo en minutos")
        print("  5. Agregar al .env: INEGI_BIE_API_TOKEN=tu-token-aqui")
        print()
        print("  Sin token, el sistema usa datos demo automáticamente.")
        print("=" * 60 + "\n")
        sys.exit(1)

    from app.connectors.inegi.bie import INDICADORES, fetch_serie
    from app.db import SessionLocal
    from app.services.bie import _upsert_registros

    estados_a_procesar = (
        {args.estado.zfill(2): ESTADOS.get(args.estado.zfill(2), args.estado)}
        if args.estado
        else ESTADOS
    )

    print("\n" + "=" * 65)
    print("  ETL BIE — INEGI Banco de Informacion Economica")
    print(f"  Serie:   historica completa")
    print(f"  Estados: {len(estados_a_procesar)}")
    print(f"  Indicadores: {', '.join(INDICADORES.keys())}")
    if args.dry_run:
        print("  MODO: DRY-RUN (no se guardará nada)")
    print("=" * 65 + "\n")

    total_registros = 0
    total_errores = 0

    for clave, nombre in sorted(estados_a_procesar.items()):
        print(f"  [{clave}] {nombre}")
        estado_total = 0
        t0 = time.time()

        for ind_key, meta in INDICADORES.items():
            try:
                registros = fetch_serie(ind_key, clave, token, recientes=False)
                estado_total += len(registros)

                if not args.dry_run and registros:
                    db = SessionLocal()
                    try:
                        _upsert_registros(db, registros)
                        db.commit()
                    finally:
                        db.close()

                status = "OK " if registros else "---"
                print(f"    [{status}] {ind_key:<18} {len(registros):>4} registros")

            except Exception as e:
                print(f"    [ERR] {ind_key:<18} {e}")
                total_errores += 1

        elapsed = time.time() - t0
        total_registros += estado_total
        print(f"        → {estado_total} registros en {elapsed:.1f}s\n")

        time.sleep(0.5)  # pausa cortés entre estados

    print("=" * 65)
    print(f"  COMPLETADO: {total_registros:,} registros cargados | {total_errores} errores")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
