"""
ETL Maestro — Marco Geoestadístico Nacional 2025 + Censo 2020

Carga en este orden:
  1. AGEBs urbanas (geometrías) → raw_data.ageb_geometries
     Fuente: data/mgn/mg_2025_integrado.zip  (00a.shp — nacional)
     Alternativa: data/mgn/01_aguascalientes.zip ... 32_zacatecas.zip
  2. Demografía AGEB → raw_data.ageb_demographics
     Fuente: data/censo_2020/RESAGEBURB_01CSV20.csv ... RESAGEBURB_32CSV20.csv
  3. Crea índice espacial si no existe
  4. Reporta totales

Uso:
  # Carga completa (MGN + Censo 2020)
  python backend/scripts/etl_mgn_maestro.py

  # Solo MGN geometrías
  python backend/scripts/etl_mgn_maestro.py --solo-mgn

  # Solo Censo 2020 (ya tienes las geometrías)
  python backend/scripts/etl_mgn_maestro.py --solo-censo

  # Solo un estado (para pruebas)
  python backend/scripts/etl_mgn_maestro.py --entidad 31
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ── Paso 1: Geometrías MGN ─────────────────────────────────────────────────────

def cargar_mgn(data_dir: Path, entidad: str | None = None) -> int:
    from load_marco_geoestadistico import load_from_zip, load_all_zips

    integrado = data_dir / "mgn" / "mg_2025_integrado.zip"
    zip_dir   = data_dir / "mgn"

    if integrado.exists():
        print(f"\n{'='*60}")
        print("PASO 1: Cargando AGEBs desde ZIP integrado nacional")
        print(f"{'='*60}")
        print(f"Archivo: {integrado}")
        print("Este archivo contiene los 32 estados. Puede tomar 10-30 min.")
        t0 = time.time()
        n = load_from_zip(str(integrado), batch_size=1000, entidad_filter=entidad)
        print(f"Tiempo: {(time.time()-t0)/60:.1f} min | {n:,} AGEBs cargadas")
        return n
    else:
        # Fallback: ZIPs por estado
        print(f"\n{'='*60}")
        print("PASO 1: Cargando AGEBs desde ZIPs por estado")
        print(f"{'='*60}")
        state_zips = sorted([z for z in zip_dir.glob("*.zip")
                             if "integrado" not in z.stem])
        if not state_zips:
            print("ERROR: No se encontraron ZIPs en data/mgn/")
            print("Descarga el MGN 2025 en: https://www.inegi.org.mx/temas/mg/")
            return 0

        if entidad:
            state_zips = [z for z in state_zips if z.stem.startswith(f"{entidad.zfill(2)}_")]

        t0 = time.time()
        n = load_all_zips(str(zip_dir), batch_size=1000)
        print(f"Tiempo: {(time.time()-t0)/60:.1f} min | {n:,} AGEBs cargadas")
        return n


# ── Paso 2: Demografía Censo 2020 ─────────────────────────────────────────────

def cargar_censo(data_dir: Path, entidad: str | None = None) -> int:
    import csv
    from datetime import datetime, timezone
    from app.db import SessionLocal
    from app.models.raw_data import AgebDemographics
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    censo_dir = data_dir / "censo_2020"
    if not censo_dir.exists():
        print(f"\nERROR: No existe el directorio {censo_dir}")
        return 0

    csvs = sorted(censo_dir.glob("RESAGEBURB_*.csv"))
    if not csvs:
        csvs = sorted(censo_dir.glob("RESAGEBURB_*.CSV"))

    if entidad:
        ent_z = entidad.zfill(2)
        csvs = [c for c in csvs if f"_{ent_z}CSV" in c.name.upper() or
                c.name.upper().replace("RESAGEBURB_", "").startswith(ent_z)]

    if not csvs:
        print(f"\nERROR: No se encontraron CSVs de Censo 2020 en {censo_dir}")
        print("Descarga en: https://www.inegi.org.mx/programas/ccpv/2020/#Datos_abiertos")
        return 0

    print(f"\n{'='*60}")
    print(f"PASO 2: Cargando demografía Censo 2020 ({len(csvs)} archivos)")
    print(f"{'='*60}")

    _TYPED_INT = [
        "POBTOT", "POBMAS", "POBFEM",
        "P_0A2", "P_3A5", "P_6A11", "P_12A14",
        "P_15A17", "P_18A24", "P_25A59", "P_60YMAS",
        "VIVTOT", "VIVPAR_HAB", "PCON_DISC", "PSINDER", "PDER_SS",
    ]
    _TYPED_FLOAT = ["PROM_OCUP", "PRO_OCUP_C", "GRAPROES"]

    def _int(v):
        try: return int(v)
        except: return None

    def _float(v):
        try: return float(v)
        except: return None

    db = SessionLocal()
    total = 0

    try:
        for csv_path in csvs:
            print(f"\n  Procesando: {csv_path.name}")
            # Usamos dict para agregar múltiples localidades que compartan ent+mun+ageb.
            # Esto evita el CardinalityViolation en ON CONFLICT DO UPDATE cuando el
            # mismo cvegeo aparece más de una vez dentro del mismo batch de INSERT.
            agg: dict = {}

            for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
                try:
                    with open(csv_path, "r", encoding=enc, errors="replace") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if str(row.get("MZA", "")).strip() != "000":
                                continue

                            ent  = str(row.get("ENTIDAD", "") or "").strip().zfill(2)
                            mun  = str(row.get("MUN", "") or "").strip().zfill(3)
                            ageb = str(row.get("AGEB", "") or "").strip()
                            # CVEGEO = ent(2)+mun(3)+ageb(4) = 9 chars — igual que MGN 2025
                            cvegeo = ent + mun + ageb

                            if len(cvegeo) < 9 or not ageb:
                                continue

                            indicadores = {}
                            for col, val in row.items():
                                col_u = col.upper()
                                if col_u in _TYPED_INT:
                                    indicadores[col_u] = _int(val)
                                elif col_u in _TYPED_FLOAT:
                                    indicadores[col_u] = _float(val)
                                elif col_u not in ("ENTIDAD", "MUN", "LOC", "AGEB", "MZA", "NOM_LOC"):
                                    indicadores[col_u] = val

                            new_pobtot  = _int(row.get("POBTOT")) or 0
                            new_p0a14   = ((_int(row.get("P_0A2"))   or 0) +
                                           (_int(row.get("P_3A5"))   or 0) +
                                           (_int(row.get("P_6A11"))  or 0) +
                                           (_int(row.get("P_12A14")) or 0))
                            new_p15a64  = ((_int(row.get("P_15A17")) or 0) +
                                           (_int(row.get("P_18A24")) or 0) +
                                           (_int(row.get("P_25A59")) or 0))

                            if cvegeo in agg:
                                # Agregar: sumar conteos, promedio ponderado para tasas
                                ex     = agg[cvegeo]
                                ex_pop = ex["pobtot"] or 0
                                ex["pobtot"]     = ex_pop + new_pobtot
                                ex["pobmas"]     = (ex["pobmas"]     or 0) + (_int(row.get("POBMAS"))    or 0)
                                ex["pobfem"]     = (ex["pobfem"]     or 0) + (_int(row.get("POBFEM"))    or 0)
                                ex["p_0a14"]     = (ex["p_0a14"]     or 0) + new_p0a14
                                ex["p_15a64"]    = (ex["p_15a64"]    or 0) + new_p15a64
                                ex["p_65ymas"]   = (ex["p_65ymas"]   or 0) + (_int(row.get("P_60YMAS"))  or 0)
                                ex["vivpar_hab"] = (ex["vivpar_hab"] or 0) + (_int(row.get("VIVPAR_HAB")) or 0)
                                ex["pcon_disc"]  = (ex["pcon_disc"]  or 0) + (_int(row.get("PCON_DISC"))  or 0)
                                ex["psinder"]    = (ex["psinder"]    or 0) + (_int(row.get("PSINDER"))    or 0)
                                ex["pder_ss"]    = (ex["pder_ss"]    or 0) + (_int(row.get("PDER_SS"))    or 0)
                                tot_pop = ex_pop + new_pobtot
                                if tot_pop > 0:
                                    for fld, col_name in [("graproes", "GRAPROES"), ("prom_ocup", "PROM_OCUP")]:
                                        new_v = _float(row.get(col_name)) or 0.0
                                        ex[fld] = ((ex[fld] or 0.0) * ex_pop + new_v * new_pobtot) / tot_pop
                            else:
                                agg[cvegeo] = {
                                    "cvegeo":      cvegeo,
                                    "fuente":      "Censo2020_AGEB_Urbana",
                                    "pobtot":      new_pobtot,
                                    "pobmas":      _int(row.get("POBMAS")),
                                    "pobfem":      _int(row.get("POBFEM")),
                                    "p_0a14":      new_p0a14,
                                    "p_15a64":     new_p15a64,
                                    "p_65ymas":    _int(row.get("P_60YMAS")),
                                    "vivpar_hab":  _int(row.get("VIVPAR_HAB")),
                                    "prom_ocup":   _float(row.get("PROM_OCUP")),
                                    "graproes":    _float(row.get("GRAPROES")),
                                    "pcon_disc":   _int(row.get("PCON_DISC")),
                                    "psinder":     _int(row.get("PSINDER")),
                                    "pder_ss":     _int(row.get("PDER_SS")),
                                    "indicadores": indicadores,
                                    "loaded_at":   datetime.now(timezone.utc),
                                }

                    # Flush en batches desde el dict ya deduplicado
                    records = list(agg.values())
                    count   = len(records)
                    for i in range(0, count, 1000):
                        _flush_censo(db, records[i : i + 1000])
                    total += count
                    db.commit()
                    print(f"  OK {count:,} AGEBs unicas cargadas")
                    break
                except UnicodeDecodeError:
                    continue

    except Exception as e:
        db.rollback()
        print(f"ERROR en Censo 2020: {e}")
        raise
    finally:
        db.close()

    return total


def _flush_censo(db, batch):
    from app.models.raw_data import AgebDemographics
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(AgebDemographics).values(batch)
    stmt = stmt.on_conflict_do_update(
        index_elements=["cvegeo"],
        set_={k: stmt.excluded[k] for k in [
            "pobtot", "pobmas", "pobfem", "p_0a14", "p_15a64", "p_65ymas",
            "vivpar_hab", "prom_ocup", "graproes", "pcon_disc",
            "psinder", "pder_ss", "indicadores", "loaded_at",
        ]},
    )
    db.execute(stmt)


# ── Paso 3: Crear índice espacial ─────────────────────────────────────────────

def crear_indices(entidad: str | None = None):
    from app.db import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        print(f"\n{'='*60}")
        print("PASO 3: Creando índices espaciales")
        print(f"{'='*60}")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ageb_geom_gist
            ON raw_data.ageb_geometries USING GIST(geom);
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ageb_ent
            ON raw_data.ageb_geometries(clave_ent);
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_demo_cvegeo
            ON raw_data.ageb_demographics(cvegeo);
        """))
        db.commit()
        print("  ✓ Índices creados")
    except Exception as e:
        db.rollback()
        print(f"  Advertencia en índices: {e}")
    finally:
        db.close()


# ── Paso 4: Reporte final ──────────────────────────────────────────────────────

def reporte_final():
    from app.db import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        q_geom = db.execute(text(
            "SELECT COUNT(*) FROM raw_data.ageb_geometries"
        )).scalar()
        q_demo = db.execute(text(
            "SELECT COUNT(*) FROM raw_data.ageb_demographics"
        )).scalar()
        q_joined = db.execute(text(
            """SELECT COUNT(*) FROM raw_data.ageb_geometries g
               JOIN raw_data.ageb_demographics d ON g.cvegeo_9 = d.cvegeo"""
        )).scalar()

        print(f"\n{'='*60}")
        print("RESUMEN FINAL")
        print(f"{'='*60}")
        print(f"  ageb_geometries  : {q_geom:>8,} registros")
        print(f"  ageb_demographics: {q_demo:>8,} registros")
        print(f"  JOIN exitoso     : {q_joined:>8,} AGEBs con geometría + demografía")
        print(f"\n  Las consultas de reporte ahora usarán AGEBs reales del MGN 2025.")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"Error en reporte: {e}")
    finally:
        db.close()


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ETL Maestro MGN 2025 + Censo 2020 → PostgreSQL/PostGIS"
    )
    parser.add_argument("--solo-mgn",   action="store_true", help="Solo carga geometrías MGN")
    parser.add_argument("--solo-censo", action="store_true", help="Solo carga demografía Censo 2020")
    parser.add_argument("--entidad",    default=None,
                        help="Número de entidad a cargar (ej. 31 para Yucatán). Omitir = todos")
    parser.add_argument("--data-dir",   default=None,
                        help="Ruta al directorio data/ (default: auto-detecta)")
    args = parser.parse_args()

    # Resolver data_dir
    script_dir = Path(__file__).resolve().parent
    data_dir = Path(args.data_dir) if args.data_dir else script_dir.parents[1] / "data"
    if not data_dir.exists():
        print(f"ERROR: No existe el directorio de datos: {data_dir}")
        sys.exit(1)

    print(f"\nPREDIK-GEO — ETL Maestro MGN 2025 + Censo 2020")
    print(f"Directorio de datos: {data_dir}")
    if args.entidad:
        print(f"Filtrando entidad: {args.entidad}")

    total_mgn   = 0
    total_censo = 0

    if not args.solo_censo:
        total_mgn = cargar_mgn(data_dir, entidad=args.entidad)

    if not args.solo_mgn:
        total_censo = cargar_censo(data_dir, entidad=args.entidad)

    if not args.solo_mgn and not args.solo_censo:
        crear_indices(entidad=args.entidad)

    reporte_final()

    print(f"ETL completado: {total_mgn:,} geom + {total_censo:,} demo")
