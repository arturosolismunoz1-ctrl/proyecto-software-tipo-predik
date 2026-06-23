"""
Carga los CSVs de "Principales resultados por AGEB y manzana urbana, 2020"
del Censo de Población y Vivienda 2020 de INEGI.

Descarga en:
  https://www.inegi.org.mx/programas/ccpv/2020/#Datos_abiertos
  → "Principales resultados por AGEB y manzana urbana, 2020"
  → Descargar por entidad o el nacional → descomprimir el ZIP.

Archivos CSV: RESAGEBURB_<EE>_2020_csv.zip → RESAGEBURB_<EE>_2020.CSV
  EE = clave de entidad (00 = nacional, 09 = CDMX, etc.)

Estructura del CSV:
  ENTIDAD, MUN, LOC, AGEB, MZA, NOM_LOC, POBTOT, POBMAS, POBFEM, ...
  Cuando MZA == "000" → total del AGEB (estas son las filas que cargamos).

Uso:
  # Un solo estado
  python backend/scripts/load_censo_2020.py --csv data/censo/RESAGEBURB_09_2020.CSV

  # Directorio con múltiples archivos (todos los que coincidan con el patrón)
  python backend/scripts/load_censo_2020.py --dir data/censo/

  # Solo guardar totales de AGEB (default). Para incluir manzanas: --manzanas
  python backend/scripts/load_censo_2020.py --csv data/censo/RESAGEBURB_09_2020.CSV --manzanas
"""
import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models.raw_data import AgebDemographics

# Columnas que se extraen con tipo específico; el resto va a JSON.
_TYPED_INT = [
    "POBTOT", "POBMAS", "POBFEM",
    "P_0A2", "P_3A5", "P_6A11", "P_12A14",
    "P_15A17", "P_18A24", "P_25A59", "P_60YMAS",
    "VIVTOT", "VIVPAR_HAB",
    "PCON_DISC", "PSINDER", "PDER_SS",
]
_TYPED_FLOAT = ["PROM_OCUP", "PRO_OCUP_C", "GRAPROES"]


def _int(val: str) -> int | None:
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _float(val: str) -> float | None:
    try:
        return float(val.replace(",", "."))
    except (ValueError, TypeError):
        return None


def _build_cvegeo(row: dict) -> str:
    ent = str(row.get("ENTIDAD", "")).strip().zfill(2)
    mun = str(row.get("MUN", "")).strip().zfill(3)
    loc = str(row.get("LOC", "")).strip().zfill(4)
    ageb = str(row.get("AGEB", "")).strip()
    return ent + mun + loc + ageb


def _row_to_record(row: dict) -> dict:
    cvegeo = _build_cvegeo(row)
    typed = {k.upper(): v for k, v in row.items()}

    # Grupos de edad sumados desde columnas individuales
    p_0a14 = sum(
        _int(typed.get(c, "") or "") or 0
        for c in ["P_0A2", "P_3A5", "P_6A11", "P_12A14"]
    )
    p_15a64 = sum(
        _int(typed.get(c, "") or "") or 0
        for c in ["P_15A17", "P_18A24", "P_25A59"]
    )
    p_65ymas = _int(typed.get("P_60YMAS", "") or "") or 0  # proxy

    return {
        "cvegeo":     cvegeo,
        "fuente":     "Censo 2020",
        "pobtot":     _int(typed.get("POBTOT", "")),
        "pobmas":     _int(typed.get("POBMAS", "")),
        "pobfem":     _int(typed.get("POBFEM", "")),
        "p_0a14":     p_0a14 or None,
        "p_15a64":    p_15a64 or None,
        "p_65ymas":   p_65ymas or None,
        "vivpar_hab": _int(typed.get("VIVPAR_HAB", "")),
        "prom_ocup":  _float(typed.get("PROM_OCUP", "")),
        "graproes":   _float(typed.get("GRAPROES", "")),
        "pcon_disc":  _int(typed.get("PCON_DISC", "")),
        "psinder":    _int(typed.get("PSINDER", "")),
        "pder_ss":    _int(typed.get("PDER_SS", "")),
        "indicadores": dict(row),
        "loaded_at":  datetime.now(timezone.utc),
    }


def _flush(db, batch: list) -> None:
    stmt = pg_insert(AgebDemographics).values(batch)
    stmt = stmt.on_conflict_do_update(
        index_elements=["cvegeo"],
        set_={k: getattr(stmt.excluded, k) for k in batch[0] if k != "cvegeo"},
    )
    db.execute(stmt)


def load_csv(path: str, include_manzanas: bool = False, batch_size: int = 1000) -> int:
    db = SessionLocal()
    total = 0
    batch = []
    skipped = 0

    try:
        with open(path, encoding="latin-1", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mza = str(row.get("MZA", "")).strip()
                is_ageb_total = mza == "000"

                if not is_ageb_total and not include_manzanas:
                    skipped += 1
                    continue

                rec = _row_to_record(row)
                if not rec["cvegeo"] or len(rec["cvegeo"]) < 9:
                    continue

                batch.append(rec)
                if len(batch) >= batch_size:
                    _flush(db, batch)
                    total += len(batch)
                    print(f"[censo] {total} registros cargados...")
                    batch.clear()

        if batch:
            _flush(db, batch)
            total += len(batch)

        db.commit()
        print(
            f"[censo] ✓ {path}: {total} registros en ageb_demographics"
            + (f" ({skipped} manzanas omitidas)" if skipped else "")
        )
        return total

    except Exception as e:
        db.rollback()
        print(f"[censo] ERROR procesando {path}: {e}")
        raise
    finally:
        db.close()


def load_directory(directory: str, include_manzanas: bool = False) -> int:
    csv_files = sorted(
        p for p in Path(directory).glob("*.CSV")
    ) + sorted(
        p for p in Path(directory).glob("*.csv")
    )
    if not csv_files:
        print(f"[censo] No se encontraron archivos CSV en {directory}")
        return 0

    total = 0
    for f in csv_files:
        print(f"[censo] Procesando {f.name}...")
        total += load_csv(str(f), include_manzanas=include_manzanas)
    print(f"[censo] ✓ Total general: {total} registros")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga CSV Censo 2020 por AGEB → PostgreSQL")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", help="Ruta a un archivo CSV (ej. data/censo/RESAGEBURB_09_2020.CSV)")
    group.add_argument("--dir", help="Directorio con múltiples CSVs del Censo")
    parser.add_argument("--manzanas", action="store_true", help="Incluir filas de manzana (MZA != 000)")
    parser.add_argument("--batch", type=int, default=1000, help="Tamaño del batch (default: 1000)")
    args = parser.parse_args()

    if args.csv:
        if not os.path.exists(args.csv):
            print(f"ERROR: No se encuentra: {args.csv}")
            sys.exit(1)
        load_csv(args.csv, include_manzanas=args.manzanas, batch_size=args.batch)
    else:
        if not os.path.isdir(args.dir):
            print(f"ERROR: No es un directorio: {args.dir}")
            sys.exit(1)
        load_directory(args.dir, include_manzanas=args.manzanas)
