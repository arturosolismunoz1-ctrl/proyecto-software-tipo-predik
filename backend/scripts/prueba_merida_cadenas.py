"""
Ejercicio: Mérida, Yucatán — Little Caesar's, Dunkin', Domino's + zonas premium INEGI.

Capas:
  - Little Caesar's  → estrella amarilla
  - Dunkin'          → estrella naranja
  - Domino's Pizza   → marcador rojo (competencia)
  - AGEBs INEGI      → coloreadas por poder adquisitivo (graproes Censo 2020)

Uso:
  python backend/scripts/prueba_merida_cadenas.py

Requiere que el servidor esté corriendo:
  make run    (o uvicorn backend.app.main:app --reload)
"""
import io
import json
import subprocess
import sys
import time
from pathlib import Path

# Forzar UTF-8 en terminal Windows para evitar UnicodeEncodeError
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --- dependencia httpx (incluida en requirements.txt) ---
try:
    import httpx
except ImportError:
    print("[!] Instala httpx: pip install httpx")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000/api/v1"
EMAIL    = "admin@predik.local"
PASSWORD = "dev_password_admin"

# Polígono que cubre el área urbana principal de Mérida, Yucatán
# (lon_min, lat_min) → (lon_max, lat_max): [-89.75, 20.85] a [-89.45, 21.10]
POLIGONO_MERIDA = {
    "type": "Polygon",
    "coordinates": [[
        [-89.75, 20.85],
        [-89.45, 20.85],
        [-89.45, 21.10],
        [-89.75, 21.10],
        [-89.75, 20.85],
    ]],
}

CAPAS = [
    {
        "keyword": "little caesars",
        "label":   "Little Caesars",
        "color":   "yellow",
        "icon":    "star",
        "estado":  "31",
    },
    {
        "keyword": "dunkin",
        "label":   "Dunkin",
        "color":   "orange",
        "icon":    "star",
        "estado":  "31",
    },
    {
        "keyword": "dominos",
        "label":   "Dominos Pizza",
        "color":   "red",
        "icon":    "circle",
        "estado":  "31",
    },
]

PAYLOAD = {
    "nombre":                  "Merida_Yucatan_Cadenas_2026",
    "polygon":                 POLIGONO_MERIDA,
    "capas":                   CAPAS,
    "formato":                 "kmz",
    "clasificacion_hexagonos": "poder_adquisitivo",
    "h3_resolution":           9,
    "ejecutar_etl":            True,
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _verificar_servidor(client: httpx.Client) -> None:
    try:
        client.get("http://localhost:8000/", timeout=5.0)
    except httpx.ConnectError:
        print("\n[!] El servidor no responde en localhost:8000")
        print("    Ejecuta primero en otra terminal:  make run")
        print("    O: uvicorn app.main:app --reload --app-dir backend\n")
        sys.exit(1)


def _login(client: httpx.Client) -> str:
    r = client.post(
        f"{BASE_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=15.0,
    )
    if r.status_code != 200:
        print(f"[!] Login fallido ({r.status_code}): {r.text}")
        sys.exit(1)
    token = r.json()["access_token"]
    print("[OK] Autenticado como admin@predik.local")
    return token


def _bd_status(client: httpx.Client, token: str) -> None:
    r = client.get(
        f"{BASE_URL}/admin/bd-status",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    if r.status_code == 200:
        data = r.json()
        print("\n[BD Status]")
        for t in data.get("tablas", []):
            emoji = "✓" if t["estado"] == "poblada" else ("~" if t["estado"] == "parcial" else "✗")
            print(f"  {emoji} {t['tabla'].split('.')[-1]:<30} {t['registros']:>10,} registros  [{t['estado']}]")
        print()


def _generar_reporte(client: httpx.Client, token: str) -> bytes:
    print("[...] Corriendo ETL para Mérida (estado 31):")
    for c in CAPAS:
        print(f"      • {c['label']}  ({c['keyword']})")
    print("[...] Generando reporte con clasificación por poder adquisitivo INEGI...")
    print("      (puede tardar 3-8 minutos en la primera ejecución)\n")

    t0 = time.time()
    r = client.post(
        f"{BASE_URL}/reporte/generar",
        json=PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
        timeout=600.0,
    )
    elapsed = time.time() - t0

    if r.status_code != 200:
        print(f"[!] Error {r.status_code}: {r.text[:500]}")
        sys.exit(1)

    print(f"[OK] Reporte generado en {elapsed:.0f}s")
    return r.content


def _abrir_kmz(path: Path) -> None:
    print(f"[...] Abriendo {path.name}...")
    try:
        subprocess.Popen(["start", "", str(path)], shell=True)
        print("[OK] KMZ abierto — verifica en Google Earth o tu visor predeterminado")
    except Exception as e:
        print(f"[!] No se pudo abrir automáticamente: {e}")
        print(f"    Abre manualmente: {path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    out_dir = Path(__file__).resolve().parents[2] / "resultados"
    out_dir.mkdir(exist_ok=True)
    kmz_path = out_dir / "merida_cadenas.kmz"

    print("\n" + "=" * 62)
    print("  PREDIK GEO - Ejercicio Merida, Yucatan")
    print("  Little Caesars [estrella amarilla]")
    print("  Dunkin'        [estrella naranja]")
    print("  Domino's Pizza [marcador rojo] (competencia)")
    print("  AGEBs INEGI    [por poder adquisitivo Censo 2020]")
    print("=" * 62 + "\n")

    with httpx.Client() as client:
        _verificar_servidor(client)
        token = _login(client)
        _bd_status(client, token)
        kmz_bytes = _generar_reporte(client, token)

    kmz_path.write_bytes(kmz_bytes)
    print(f"\n[OK] KMZ guardado en: {kmz_path}")
    print(f"     Tamaño: {len(kmz_bytes):,} bytes")

    _abrir_kmz(kmz_path)
    print("\n" + "=" * 62)


if __name__ == "__main__":
    main()
