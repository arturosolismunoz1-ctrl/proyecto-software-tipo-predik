"""
Computa score_nse y nse_nivel para todos los AGEBs en raw_data.ageb_demographics.

Fórmula (score 0-100):
  - Educación     34 pts  graproes / 16 (Posgrado = máximo)
  - Computadora   24 pts  VPH_PC   / vivpar_hab
  - Seg. Social   27 pts  pder_ss  / pobtot
  - Internet       9 pts  VPH_INTER / vivpar_hab
  - Automóvil      6 pts  VPH_AUTOM / vivpar_hab
  Total          100 pts

Umbrales calibrados con distribución AMAI 2020 (nacional):
  A/B   >= 67  (  7.2 % hogares)
  C+    >= 57  ( 14.2 %)
  C     >= 50  ( 17.0 %)
  C-    >= 42  ( 18.7 %)
  D+    >= 35  ( 18.4 %)
  D     >= 25  ( 18.5 %)
  E     <  25  (  6.0 %)

Uso:
  # Contra BD local
  python backend/scripts/compute_nse_scores.py

  # Contra Supabase
  DATABASE_URL="postgresql+psycopg2://..." python backend/scripts/compute_nse_scores.py

  # Solo mostrar distribución sin escribir
  python backend/scripts/compute_nse_scores.py --dry-run
"""
import argparse
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Forzar UTF-8 en stdout para evitar cp1252 en Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import psycopg2
import psycopg2.extras

# Distribución AMAI 2020 (% hogares México, de mayor a menor nivel)
# El percentil de corte = 100 - acumulado_superior
_AMAI_DIST = [
    ("AB",      7.2),
    ("Cmas",   14.2),
    ("C",      17.0),
    ("Cmenos", 18.7),
    ("Dmas",   18.4),
    ("D",      18.5),
    ("E",       6.0),
]
_AMAI_REF = {k: v for k, v in _AMAI_DIST}


def calcular_thresholds(scores_sorted: list) -> list:
    """
    Deriva umbrales de score para que la distribución coincida con AMAI nacional.
    scores_sorted: lista ascendente. Retorna [(nivel, umbral), ...] de mayor a menor,
    excluyendo E (que es el catch-all implícito para lo que queda debajo).
    """
    n = len(scores_sorted)
    thresholds = []
    acum = 0.0
    # Solo hasta D (excluir E — es el fallback implícito)
    niveles_con_umbral = [row for row in _AMAI_DIST if row[0] != "E"]
    for nivel, pct in niveles_con_umbral:
        acum += pct
        # El umbral para este nivel: score en el percentil (100 - acum)
        # Los AGEBs con score >= umbral pertenecen a este nivel o superior
        idx = int(n * (1.0 - acum / 100.0))
        idx = max(0, min(idx, n - 1))
        umbral = scores_sorted[idx]
        thresholds.append((nivel, round(umbral, 2)))
    return thresholds


def asignar_nivel_con_thresholds(score: float, thresholds: list) -> str:
    """E es el nivel implícito para todo lo que quede debajo del umbral más bajo."""
    for nivel, umbral in thresholds:
        if score >= umbral:
            return nivel
    return "E"


def _vph(ind: dict, key: str) -> float:
    v = ind.get(key) or ind.get(key.lower()) or 0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def calcular_score(row: dict) -> float:
    """Score NSE 0-100 para un AGEB."""
    viv = max(float(row.get("vivpar_hab") or 1), 1)
    pop = max(float(row.get("pobtot") or 1), 1)
    ind = row.get("indicadores") or {}

    edu      = min((float(row.get("graproes") or 0)) / 16.0, 1.0) * 34
    pc       = min(_vph(ind, "VPH_PC")    / viv, 1.0) * 24
    ss       = min(float(row.get("pder_ss") or 0) / pop, 1.0) * 27
    internet = min(_vph(ind, "VPH_INTER") / viv, 1.0) *  9
    auto     = min(_vph(ind, "VPH_AUTOM") / viv, 1.0) *  6

    return round(edu + pc + ss + internet + auto, 2)


def asignar_nivel(score: float) -> str:
    for nivel, umbral in _NIVELES:
        if score >= umbral:
            return nivel
    return "E"


def _dsn(url: str) -> str:
    """Convierte DATABASE_URL a DSN de psycopg2."""
    return url.replace("postgresql+psycopg2://", "postgresql://")


def main():
    parser = argparse.ArgumentParser(description="Computa score NSE para AGEBs")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra distribución, no escribe")
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        # Intentar URL local por defecto
        db_url = "postgresql://admin:dev_password_local@localhost:5432/geodata_predik_clone"
        print(f"DATABASE_URL no definida — usando BD local: {db_url.split('@')[1]}")

    dsn = _dsn(db_url)

    print(f"\n{'='*60}")
    print("  NSE Score — Cómputo y asignación de niveles")
    print(f"  Modo: {'DRY-RUN (no escribe)' if args.dry_run else 'ESCRITURA'}")
    print(f"{'='*60}\n")

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Leer todos los AGEBs
    print("Leyendo AGEBs...", end=" ", flush=True)
    cur.execute("""
        SELECT cvegeo, graproes, vivpar_hab, pobtot, pder_ss, indicadores
        FROM raw_data.ageb_demographics
    """)
    rows = cur.fetchall()
    print(f"{len(rows):,} AGEBs")

    if not rows:
        print("No hay datos. Ejecutar primero: load_censo_2020.py")
        return

    # Calcular scores
    # AGEBs con vivpar_hab=0 o sin indicadores → score_nse=0, nivel=E (sin datos)
    scores_raw = []
    for row in rows:
        r = dict(row)
        viv = r.get("vivpar_hab") or 0
        ind = r.get("indicadores") or {}
        if viv == 0 or (not ind):
            scores_raw.append((0.0, "E", r["cvegeo"]))
        else:
            scores_raw.append((calcular_score(r), None, r["cvegeo"]))

    # Solo los que tienen datos reales para calibrar umbrales
    con_datos = [(s, cv) for s, n, cv in scores_raw if n is None]
    scores_sorted = sorted(s for s, _ in con_datos)

    # Derivar umbrales para que la distribución coincida con AMAI
    thresholds = calcular_thresholds(scores_sorted)

    print("\n-- Umbrales calibrados con datos del dataset -----------------")
    print(f"{'Nivel':<8} {'Score min':>10}  {'AMAI %':>6}")
    print("-" * 35)
    for nivel, umbral in thresholds:
        print(f"{nivel:<8} {umbral:>10.2f}  {_AMAI_REF[nivel]:>5.1f}%")

    # Asignar niveles: los pre-clasificados como E se mantienen; el resto usa thresholds
    resultados = []
    for score, nivel_pre, cvegeo in scores_raw:
        if nivel_pre == "E":
            resultados.append((score, "E", cvegeo))
        else:
            nivel = asignar_nivel_con_thresholds(score, thresholds)
            resultados.append((score, nivel, cvegeo))

    # Distribución obtenida
    conteo = Counter(n for _, n, _ in resultados)
    total = len(resultados)

    print("\n-- Distribucion obtenida vs AMAI referencia ------------------")
    print(f"{'Nivel':<8} {'N':>6}  {'%':>6}  {'AMAI %':>6}  {'Diferencia':>10}")
    print("-" * 50)
    for nivel, _ in _AMAI_DIST:
        n = conteo.get(nivel, 0)
        pct = n / total * 100
        ref = _AMAI_REF.get(nivel, 0)
        diff = pct - ref
        signo = "+" if diff >= 0 else ""
        print(f"{nivel:<8} {n:>6,}  {pct:>5.1f}%  {ref:>5.1f}%  {signo}{diff:>8.1f}%")
    print("-" * 50)
    print(f"{'Total':<8} {total:>6,}  100.0%")

    # Score stats (sobre AGEBs con datos)
    scores = scores_sorted
    p25 = scores[int(len(scores) * 0.25)]
    p50 = scores[int(len(scores) * 0.50)]
    p75 = scores[int(len(scores) * 0.75)]
    p93 = scores[int(len(scores) * 0.928)]
    print(f"\n-- Score stats -----------------------------------------------")
    print(f"  Min: {scores[0]:.1f}   P25: {p25:.1f}   P50: {p50:.1f}   P75: {p75:.1f}   P93: {p93:.1f}   Max: {scores[-1]:.1f}")

    if args.dry_run:
        print("\nDRY-RUN: no se escribió nada.")
        conn.close()
        return

    # Escribir a BD en batches
    print(f"\nEscribiendo {total:,} AGEBs...")
    BATCH = 2000
    escritos = 0
    upd_cur = conn.cursor()
    data = [(s, n, cv) for s, n, cv in resultados]

    for i in range(0, len(data), BATCH):
        batch = data[i:i + BATCH]
        psycopg2.extras.execute_values(
            upd_cur,
            """
            UPDATE raw_data.ageb_demographics AS d
            SET score_nse = v.score, nse_nivel = v.nivel
            FROM (VALUES %s) AS v(score, nivel, cvegeo)
            WHERE d.cvegeo = v.cvegeo
            """,
            batch,
            template="(%s::float, %s::varchar, %s::varchar)",
        )
        escritos += len(batch)
        pct = escritos / total * 100
        print(f"  [{pct:5.1f}%] {escritos:,}/{total:,}", end="\r", flush=True)

    conn.commit()
    upd_cur.close()
    cur.close()
    conn.close()

    print(f"\n\nCompletado: {escritos:,} AGEBs actualizados a las {datetime.now().strftime('%H:%M:%S')}")
    print(f"\nSiguiente paso — si vas a usar Supabase, corre también:")
    print(f"  $env:DATABASE_URL='postgresql+psycopg2://...supabase...'")
    print(f"  python backend/scripts/compute_nse_scores.py\n")


if __name__ == "__main__":
    main()
