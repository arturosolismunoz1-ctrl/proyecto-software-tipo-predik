"""
Migración selectiva local → Supabase
Estados: 09 (CDMX) y 31 (Yucatán)

Ejecutar desde la raíz del proyecto:
  python backend/scripts/migrate_to_supabase.py

Flags:
  --dry-run   Solo muestra conteos, no migra
  --tabla     Migrar solo una tabla: agebs|demographics|manzanas|denue|bie
  --reset     Borra checkpoints guardados y empieza desde cero
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
import psycopg2.extensions

# ── Configuración ─────────────────────────────────────────────────────────────

ESTADOS = ("09", "31")
NOMBRES_ESTADOS = {"09": "CDMX", "31": "Yucatán"}
BATCH_SIZE_GEOM = 300    # filas con geometría grande (manzanas)
BATCH_SIZE_AGEB = 800    # AGEBs (geometría mediana)
BATCH_SIZE_DENUE = 2000  # DENUE (solo POINT, sin raw_response)
BATCH_SIZE_SMALL = 5000  # tablas sin geometría

CHECKPOINT_FILE = Path(__file__).parent / ".migrate_checkpoint.json"

LOCAL_DSN  = "postgresql://admin:dev_password_local@localhost:5432/geodata_predik_clone"

# Intentar IPv6 directo primero; si falla, usar pooler
SUPA_DIRECT = (
    "postgresql://postgres.goemltxlnlxknlgembxk:-9%23XJi%2BncpCnXii"
    "@db.goemltxlnlxknlgembxk.supabase.co:5432/postgres?sslmode=require"
)
SUPA_POOLER = (
    "postgresql://postgres.goemltxlnlxknlgembxk:-9%23XJi%2BncpCnXii"
    "@aws-1-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require"
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {level:5s} {msg}", flush=True)


def conectar_supabase() -> psycopg2.extensions.connection:
    for dsn, label in [(SUPA_DIRECT, "IPv6 directo"), (SUPA_POOLER, "pooler IPv4")]:
        try:
            conn = psycopg2.connect(dsn, connect_timeout=15)
            log(f"Supabase conectado vía {label}")
            return conn
        except Exception as e:
            log(f"  {label} falló: {e}", "WARN")
    raise RuntimeError("No se pudo conectar a Supabase por ninguna ruta.")


def contar(cur, tabla: str, where: str = "") -> int:
    q = f"SELECT COUNT(*) FROM {tabla}"
    if where:
        q += f" WHERE {where}"
    cur.execute(q)
    return cur.fetchone()[0]


def checkpoint_load() -> dict:
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return {}


def checkpoint_save(data: dict) -> None:
    CHECKPOINT_FILE.write_text(json.dumps(data, indent=2))


def barra(actual: int, total: int, label: str = "") -> str:
    pct = actual / max(total, 1) * 100
    done = int(pct / 5)
    bar = "#" * done + "." * (20 - done)
    return f"[{bar}] {pct:5.1f}% {actual:,}/{total:,} {label}"

# ── Verificación previa ───────────────────────────────────────────────────────

def verificar_conexiones(src, dst) -> bool:
    ok = True
    src_cur = src.cursor()
    dst_cur = dst.cursor()

    tablas = [
        ("raw_data.ageb_geometries",      f"clave_ent IN {ESTADOS}"),
        ("raw_data.ageb_demographics",    "cvegeo LIKE '09%' OR cvegeo LIKE '31%'"),
        ("raw_data.manzana_vivienda",     f"clave_ent IN {ESTADOS}"),
        ("raw_data.denue_establishments", "entidad ILIKE 'CIUDAD DE M%XICO' OR entidad ILIKE 'YUCAT%N'"),
        ("raw_data.bie_indicadores",      f"estado_clave IN {ESTADOS}"),
    ]
    log("--- Conteos fuente (local) -----------------------------------")
    total_src = 0
    for tabla, where in tablas:
        n = contar(src_cur, tabla, where)
        total_src += n
        log(f"  {tabla:45s} {n:>10,}")

    log("--- Conteos destino (Supabase) -------------------------------")
    for tabla, _ in tablas:
        try:
            n = contar(dst_cur, tabla)
            log(f"  {tabla:45s} {n:>10,}")
        except Exception as e:
            log(f"  {tabla}: {e}", "ERROR")
            ok = False

    log(f"  Total registros a migrar: {total_src:,}")
    return ok


# ── Migración 1: ageb_geometries ─────────────────────────────────────────────

def migrar_ageb_geometries(src, dst, dry_run: bool, cp: dict) -> int:
    tabla = "ageb_geometries"
    if cp.get(tabla) == "done":
        log(f"  {tabla}: ya completado (checkpoint). Saltando.")
        return 0

    src_cur = src.cursor(f"cur_{tabla}", cursor_factory=psycopg2.extras.RealDictCursor)
    src_cur.execute(f"""
        SELECT cvegeo, clave_ent, clave_mun, cve_loc, cve_ageb,
               nom_ent, nom_mun, nom_loc, ambito, cvegeo_9,
               ST_AsBinary(geom) AS geom_wkb, loaded_at
        FROM raw_data.ageb_geometries
        WHERE clave_ent IN {ESTADOS}
        ORDER BY clave_ent, cvegeo
    """)

    total_src = contar(src.cursor(), "raw_data.ageb_geometries", f"clave_ent IN {ESTADOS}")
    log(f"  {tabla}: {total_src:,} registros a migrar")
    if dry_run:
        src_cur.close()
        return total_src

    dst_cur = dst.cursor()
    migrados = cp.get(f"{tabla}_offset", 0)
    if migrados:
        log(f"  Reanudando desde fila {migrados:,}")
        src_cur.fetchmany(migrados)

    t0 = time.time()
    while True:
        rows = src_cur.fetchmany(BATCH_SIZE_AGEB)
        if not rows:
            break
        data = [
            (r["cvegeo"], r["clave_ent"], r["clave_mun"], r["cve_loc"], r["cve_ageb"],
             r["nom_ent"], r["nom_mun"], r["nom_loc"], r["ambito"], r["cvegeo_9"],
             bytes(r["geom_wkb"]), r["loaded_at"])
            for r in rows
        ]
        psycopg2.extras.execute_values(
            dst_cur, """
            INSERT INTO raw_data.ageb_geometries
              (cvegeo, clave_ent, clave_mun, cve_loc, cve_ageb,
               nom_ent, nom_mun, nom_loc, ambito, cvegeo_9, geom, loaded_at)
            VALUES %s
            ON CONFLICT (cvegeo) DO NOTHING
            """,
            data,
            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromWKB(%s::bytea,4326),%s)",
            page_size=BATCH_SIZE_AGEB,
        )
        dst.commit()
        migrados += len(rows)
        cp[f"{tabla}_offset"] = migrados
        checkpoint_save(cp)
        vel = migrados / max(time.time() - t0, 0.1)
        log(f"  {barra(migrados, total_src, f'({vel:.0f}/s)')}")

    dst_cur.close()
    src_cur.close()
    cp[tabla] = "done"
    checkpoint_save(cp)
    log(f"  {tabla}: COMPLETADO — {migrados:,} filas en {(time.time()-t0)/60:.1f} min")
    return migrados


# ── Migración 2: ageb_demographics ───────────────────────────────────────────

def migrar_ageb_demographics(src, dst, dry_run: bool, cp: dict) -> int:
    tabla = "ageb_demographics"
    if cp.get(tabla) == "done":
        log(f"  {tabla}: ya completado (checkpoint). Saltando.")
        return 0

    where = "cvegeo LIKE '09%' OR cvegeo LIKE '31%'"
    total_src = contar(src.cursor(), f"raw_data.{tabla}", where)
    log(f"  {tabla}: {total_src:,} registros a migrar")
    if dry_run:
        return total_src

    src_cur = src.cursor(f"cur_{tabla}", cursor_factory=psycopg2.extras.RealDictCursor)
    src_cur.execute(f"""
        SELECT cvegeo, fuente, pobtot, pobmas, pobfem,
               p_0a14, p_15a64, p_65ymas, vivpar_hab, prom_ocup,
               graproes, pcon_disc, psinder, pder_ss, indicadores, loaded_at
        FROM raw_data.ageb_demographics
        WHERE {where}
        ORDER BY cvegeo
    """)

    dst_cur = dst.cursor()
    migrados = cp.get(f"{tabla}_offset", 0)
    if migrados:
        src_cur.fetchmany(migrados)

    t0 = time.time()
    while True:
        rows = src_cur.fetchmany(BATCH_SIZE_SMALL)
        if not rows:
            break
        data = [
            (r["cvegeo"], r["fuente"], r["pobtot"], r["pobmas"], r["pobfem"],
             r["p_0a14"], r["p_15a64"], r["p_65ymas"], r["vivpar_hab"], r["prom_ocup"],
             r["graproes"], r["pcon_disc"], r["psinder"], r["pder_ss"],
             json.dumps(r["indicadores"]) if r["indicadores"] else None, r["loaded_at"])
            for r in rows
        ]
        psycopg2.extras.execute_values(
            dst_cur, """
            INSERT INTO raw_data.ageb_demographics
              (cvegeo, fuente, pobtot, pobmas, pobfem,
               p_0a14, p_15a64, p_65ymas, vivpar_hab, prom_ocup,
               graproes, pcon_disc, psinder, pder_ss, indicadores, loaded_at)
            VALUES %s
            ON CONFLICT (cvegeo) DO NOTHING
            """,
            data, page_size=BATCH_SIZE_SMALL,
        )
        dst.commit()
        migrados += len(rows)
        cp[f"{tabla}_offset"] = migrados
        checkpoint_save(cp)
        log(f"  {barra(migrados, total_src)}")

    dst_cur.close()
    src_cur.close()
    cp[tabla] = "done"
    checkpoint_save(cp)
    log(f"  {tabla}: COMPLETADO — {migrados:,} filas en {(time.time()-t0)/60:.1f} min")
    return migrados


# ── Migración 3: manzana_vivienda ─────────────────────────────────────────────

def migrar_manzanas(src, dst, dry_run: bool, cp: dict) -> int:
    tabla = "manzana_vivienda"
    if cp.get(tabla) == "done":
        log(f"  {tabla}: ya completado (checkpoint). Saltando.")
        return 0

    total_src = contar(src.cursor(), f"raw_data.{tabla}", f"clave_ent IN {ESTADOS}")
    log(f"  {tabla}: {total_src:,} registros a migrar (la más lenta, ~60-90 min)")
    if dry_run:
        return total_src

    src_cur = src.cursor(f"cur_{tabla}", cursor_factory=psycopg2.extras.RealDictCursor)
    src_cur.execute(f"""
        SELECT cvegeo, clave_ent, clave_mun, cve_loc, cve_ageb, cve_mza, cvegeo_ageb,
               vivtot, vivpar, vivpar_hab, con_agua, con_dren, con_luz,
               ST_AsBinary(geom) AS geom_wkb, indicadores, fuente, loaded_at
        FROM raw_data.manzana_vivienda
        WHERE clave_ent IN {ESTADOS}
        ORDER BY clave_ent, cvegeo
    """)

    dst_cur = dst.cursor()
    migrados = cp.get(f"{tabla}_offset", 0)
    if migrados:
        log(f"  Reanudando desde fila {migrados:,}")
        src_cur.fetchmany(migrados)

    t0 = time.time()
    while True:
        rows = src_cur.fetchmany(BATCH_SIZE_GEOM)
        if not rows:
            break
        data = [
            (r["cvegeo"], r["clave_ent"], r["clave_mun"], r["cve_loc"],
             r["cve_ageb"], r["cve_mza"], r["cvegeo_ageb"],
             r["vivtot"], r["vivpar"], r["vivpar_hab"],
             r["con_agua"], r["con_dren"], r["con_luz"],
             bytes(r["geom_wkb"]) if r["geom_wkb"] else None,
             json.dumps(r["indicadores"]) if r["indicadores"] else None,
             r["fuente"], r["loaded_at"])
            for r in rows
        ]
        psycopg2.extras.execute_values(
            dst_cur, """
            INSERT INTO raw_data.manzana_vivienda
              (cvegeo, clave_ent, clave_mun, cve_loc, cve_ageb, cve_mza, cvegeo_ageb,
               vivtot, vivpar, vivpar_hab, con_agua, con_dren, con_luz,
               geom, indicadores, fuente, loaded_at)
            VALUES %s
            ON CONFLICT (cvegeo) DO NOTHING
            """,
            data,
            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromWKB(%s::bytea,4326),%s,%s,%s)",
            page_size=BATCH_SIZE_GEOM,
        )
        dst.commit()
        migrados += len(rows)
        cp[f"{tabla}_offset"] = migrados
        checkpoint_save(cp)
        eta_s = (total_src - migrados) / max(migrados / (time.time() - t0), 0.1)
        eta_min = int(eta_s / 60)
        log(f"  {barra(migrados, total_src, f'ETA ~{eta_min} min')}")

    dst_cur.close()
    src_cur.close()
    cp[tabla] = "done"
    checkpoint_save(cp)
    log(f"  {tabla}: COMPLETADO — {migrados:,} filas en {(time.time()-t0)/60:.1f} min")
    return migrados


# ── Migración 4: denue_establishments ────────────────────────────────────────

DENUE_FILTER = (
    "entidad ILIKE 'CIUDAD DE M%XICO' "
    "OR entidad ILIKE 'YUCAT%N'"
)

def migrar_denue(src, dst, dry_run: bool, cp: dict) -> int:
    tabla = "denue_establishments"
    if cp.get(tabla) == "done":
        log(f"  {tabla}: ya completado (checkpoint). Saltando.")
        return 0

    total_src = contar(src.cursor(), f"raw_data.{tabla}", DENUE_FILTER)
    log(f"  {tabla}: {total_src:,} registros a migrar (raw_response → NULL)")
    if dry_run:
        return total_src

    src_cur = src.cursor(f"cur_{tabla}", cursor_factory=psycopg2.extras.RealDictCursor)
    src_cur.execute(f"""
        SELECT clee, nombre, razon_social, clase_actividad, codigo_scian,
               estrato_personal, entidad, municipio, localidad, colonia, cp,
               ST_AsBinary(geom) AS geom_wkb, fuente_actualizacion, fetched_at
        FROM raw_data.denue_establishments
        WHERE {DENUE_FILTER}
        ORDER BY id
    """)

    dst_cur = dst.cursor()
    migrados = cp.get(f"{tabla}_offset", 0)
    if migrados:
        log(f"  Reanudando desde fila {migrados:,}")
        src_cur.fetchmany(migrados)

    t0 = time.time()
    while True:
        rows = src_cur.fetchmany(BATCH_SIZE_DENUE)
        if not rows:
            break
        data = [
            (r["clee"], r["nombre"], r["razon_social"], r["clase_actividad"],
             r["codigo_scian"], r["estrato_personal"], r["entidad"], r["municipio"],
             r["localidad"], r["colonia"], r["cp"],
             bytes(r["geom_wkb"]) if r["geom_wkb"] else None,
             r["fuente_actualizacion"], r["fetched_at"])
            for r in rows
        ]
        psycopg2.extras.execute_values(
            dst_cur, """
            INSERT INTO raw_data.denue_establishments
              (clee, nombre, razon_social, clase_actividad, codigo_scian,
               estrato_personal, entidad, municipio, localidad, colonia, cp,
               geom, fuente_actualizacion, fetched_at, raw_response)
            VALUES %s
            ON CONFLICT (clee) DO NOTHING
            """,
            data,
            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromWKB(%s::bytea,4326),%s,%s,NULL)",
            page_size=BATCH_SIZE_DENUE,
        )
        dst.commit()
        migrados += len(rows)
        cp[f"{tabla}_offset"] = migrados
        checkpoint_save(cp)
        vel = migrados / max(time.time() - t0, 0.1)
        log(f"  {barra(migrados, total_src, f'({vel:.0f}/s)')}")

    dst_cur.close()
    src_cur.close()
    cp[tabla] = "done"
    checkpoint_save(cp)
    log(f"  {tabla}: COMPLETADO — {migrados:,} filas en {(time.time()-t0)/60:.1f} min")
    return migrados


# ── Migración 5: bie_indicadores ─────────────────────────────────────────────

def migrar_bie(src, dst, dry_run: bool, cp: dict) -> int:
    tabla = "bie_indicadores"
    if cp.get(tabla) == "done":
        log(f"  {tabla}: ya completado (checkpoint). Saltando.")
        return 0

    where = f"estado_clave IN {ESTADOS}"
    total_src = contar(src.cursor(), f"raw_data.{tabla}", where)
    log(f"  {tabla}: {total_src:,} registros a migrar")
    if dry_run:
        return total_src

    if total_src == 0:
        log(f"  {tabla}: sin datos para los estados seleccionados. Saltando.")
        cp[tabla] = "done"
        checkpoint_save(cp)
        return 0

    src_cur = src.cursor(f"cur_{tabla}", cursor_factory=psycopg2.extras.RealDictCursor)
    src_cur.execute(f"""
        SELECT indicador_id, nombre, descripcion, unidad, frecuencia,
               area_clave, estado_clave, periodo, periodo_fecha,
               valor, fuente, loaded_at
        FROM raw_data.bie_indicadores
        WHERE {where}
        ORDER BY id
    """)

    dst_cur = dst.cursor()
    t0 = time.time()
    migrados = 0
    while True:
        rows = src_cur.fetchmany(BATCH_SIZE_SMALL)
        if not rows:
            break
        data = [
            (r["indicador_id"], r["nombre"], r["descripcion"], r["unidad"], r["frecuencia"],
             r["area_clave"], r["estado_clave"], r["periodo"], r["periodo_fecha"],
             r["valor"], r["fuente"], r["loaded_at"])
            for r in rows
        ]
        psycopg2.extras.execute_values(
            dst_cur, """
            INSERT INTO raw_data.bie_indicadores
              (indicador_id, nombre, descripcion, unidad, frecuencia,
               area_clave, estado_clave, periodo, periodo_fecha,
               valor, fuente, loaded_at)
            VALUES %s
            ON CONFLICT (indicador_id, area_clave, periodo) DO NOTHING
            """,
            data, page_size=BATCH_SIZE_SMALL,
        )
        dst.commit()
        migrados += len(rows)
        log(f"  {barra(migrados, total_src)}")

    dst_cur.close()
    src_cur.close()
    cp[tabla] = "done"
    checkpoint_save(cp)
    log(f"  {tabla}: COMPLETADO — {migrados:,} filas en {(time.time()-t0)/60:.1f} min")
    return migrados


# ── Verificación final ────────────────────────────────────────────────────────

def verificar_resultado(src, dst) -> None:
    log("=" * 60)
    log("VERIFICACION FINAL")
    log("=" * 60)

    checks = [
        ("raw_data.ageb_geometries",   f"clave_ent IN {ESTADOS}",   f"clave_ent IN {ESTADOS}"),
        ("raw_data.ageb_demographics", "cvegeo LIKE '09%' OR cvegeo LIKE '31%'",
                                       "cvegeo LIKE '09%' OR cvegeo LIKE '31%'"),
        ("raw_data.manzana_vivienda",  f"clave_ent IN {ESTADOS}",   f"clave_ent IN {ESTADOS}"),
        ("raw_data.denue_establishments", DENUE_FILTER, DENUE_FILTER),
        ("raw_data.bie_indicadores",   f"estado_clave IN {ESTADOS}", f"estado_clave IN {ESTADOS}"),
    ]

    todos_ok = True
    for tabla, where_src, where_dst in checks:
        n_src = contar(src.cursor(), tabla, where_src)
        n_dst = contar(dst.cursor(), tabla, where_dst)
        ok = n_src == n_dst
        todos_ok = todos_ok and ok
        estado = "✅" if ok else "❌"
        log(f"  {estado} {tabla}")
        log(f"       local={n_src:,}  |  supabase={n_dst:,}")

    # Verificar geometrías válidas en Supabase
    dst_cur = dst.cursor()
    for tabla, col in [("raw_data.ageb_geometries", "geom"),
                       ("raw_data.manzana_vivienda", "geom")]:
        dst_cur.execute(f"SELECT COUNT(*) FROM {tabla} WHERE NOT ST_IsValid({col}) AND {col} IS NOT NULL")
        invalidas = dst_cur.fetchone()[0]
        if invalidas:
            log(f"  [!!] {tabla}: {invalidas} geometrias invalidas", "WARN")
        else:
            log(f"  [OK] {tabla}: todas las geometrias validas")

    log("=" * 60)
    if todos_ok:
        log("[OK] MIGRACION COMPLETADA CON EXITO")
    else:
        log("[!!] MIGRACION CON DIFERENCIAS - revisar conteos arriba", "ERROR")


# ── Main ──────────────────────────────────────────────────────────────────────

TABLAS_MAP = {
    "agebs":        migrar_ageb_geometries,
    "demographics": migrar_ageb_demographics,
    "manzanas":     migrar_manzanas,
    "denue":        migrar_denue,
    "bie":          migrar_bie,
}

def main() -> None:
    parser = argparse.ArgumentParser(description="Migración local → Supabase (09 CDMX + 31 Yucatán)")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra conteos, no migra")
    parser.add_argument("--tabla", choices=list(TABLAS_MAP.keys()), help="Migrar solo esta tabla")
    parser.add_argument("--reset", action="store_true", help="Borra checkpoints y empieza de cero")
    args = parser.parse_args()

    if args.reset and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        log("Checkpoints borrados.")

    log("=" * 60)
    log("MIGRACION predik-geo -> Supabase")
    log(f"Estados: {', '.join(f'{k} ({v})' for k, v in NOMBRES_ESTADOS.items())}")
    log(f"Modo: {'DRY RUN' if args.dry_run else 'REAL'}")
    log("=" * 60)

    log("Conectando a BD local...")
    src = psycopg2.connect(LOCAL_DSN)

    log("Conectando a Supabase...")
    dst = conectar_supabase()

    cp = checkpoint_load()

    # Mostrar estado de origen y destino
    verificar_conexiones(src, dst)

    if args.dry_run:
        log("Modo dry-run: sin cambios. Saliendo.")
        return

    log("=" * 60)
    t_total = time.time()

    tablas_a_migrar = (
        {args.tabla: TABLAS_MAP[args.tabla]} if args.tabla else TABLAS_MAP
    )

    total_migrados = 0
    for nombre, fn in tablas_a_migrar.items():
        log(f"\n-- {nombre.upper()} " + "-"*40)
        n = fn(src, dst, args.dry_run, cp)
        total_migrados += n

    log("\n")
    verificar_resultado(src, dst)

    elapsed = (time.time() - t_total) / 60
    log(f"Tiempo total: {elapsed:.1f} min | {total_migrados:,} filas migradas")

    # Limpiar checkpoint al completar todo
    if not args.tabla and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        log("Checkpoints limpiados.")

    src.close()
    dst.close()


if __name__ == "__main__":
    main()
