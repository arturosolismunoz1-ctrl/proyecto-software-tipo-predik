"""
Genera un KMZ con capas de papelerias en Ecatepec consumiendo exclusivamente la API:
  - POST /api/v1/zona/concentracion-comercial  -> hexagonos H3 coloreados por densidad
  - POST /api/v1/zona/establecimientos         -> puntos individuales de papelerias

Uso:
  python backend/scripts/generar_kmz_ecatepec.py
  python backend/scripts/generar_kmz_ecatepec.py --output resultados/ecatepec.kmz
"""
import argparse
import os
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape
import json

import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")
EMAIL    = os.getenv("PREDIK_EMAIL", "admin@predik.local")
PASSWORD = os.getenv("PREDIK_PASSWORD", "dev_password_admin")

ECATEPEC_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [-99.10, 19.55],
        [-98.94, 19.55],
        [-98.94, 19.76],
        [-99.10, 19.76],
        [-99.10, 19.55],
    ]],
}


# ── Auth ───────────────────────────────────────────────────────────────────────

def login() -> str:
    r = requests.post(f"{API_BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


# ── Consultas API ──────────────────────────────────────────────────────────────

def get_hexagonos(token: str) -> tuple[list[dict], int]:
    """Llama concentracion-comercial y devuelve (celdas_heatmap, total)."""
    r = requests.post(
        f"{API_BASE}/zona/concentracion-comercial",
        json={"geometry": ECATEPEC_POLYGON},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data["celdas_heatmap"], data["total_establecimientos"]


def get_puntos(token: str) -> list[dict]:
    """Llama establecimientos con keyword=papeleria y devuelve lista de puntos."""
    r = requests.post(
        f"{API_BASE}/zona/establecimientos",
        json={"geometry": ECATEPEC_POLYGON, "keyword": "papeleria"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["establecimientos"]


# ── Color ──────────────────────────────────────────────────────────────────────

def _kml_color(cantidad: int, max_cantidad: int, alpha: int = 0xCC) -> str:
    """Color KML AABBGGRR interpolando verde -> amarillo -> naranja -> rojo."""
    ratio = 0.0 if max_cantidad <= 1 else min(1.0, (cantidad - 1) / (max_cantidad - 1))

    if ratio < 0.33:
        t = ratio / 0.33
        r, g, b = int(t * 255), 200, 0
    elif ratio < 0.66:
        t = (ratio - 0.33) / 0.33
        r, g, b = 255, int(200 - t * 128), 0
    else:
        t = (ratio - 0.66) / 0.34
        r, g, b = 255, int(72 - t * 72), 0

    return f"{alpha:02X}{b:02X}{g:02X}{r:02X}"


# ── KML ────────────────────────────────────────────────────────────────────────

def _geojson_polygon_to_kml_coords(geom_str: str) -> str:
    """Convierte GeoJSON Polygon/MultiPolygon string a coordenadas KML."""
    geom = json.loads(geom_str)
    if geom["type"] == "Polygon":
        ring = geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        ring = geom["coordinates"][0][0]
    else:
        return ""
    return " ".join(f"{c[0]:.6f},{c[1]:.6f},0" for c in ring)


def generate_kml(hexagonos: list[dict], puntos: list[dict], total: int) -> str:
    max_cantidad = max((h["cantidad"] for h in hexagonos), default=1)
    unique_counts = sorted(set(h["cantidad"] for h in hexagonos))

    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>')
    L.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
    L.append('<Document>')
    L.append('  <name>Papelerias Ecatepec — Predik Geo</name>')
    L.append(f'  <description><![CDATA[<b>{len(puntos)} papelerias</b> | {len(hexagonos)} celdas H3<br/>Ecatepec de Morelos, Estado de Mexico<br/>Fuente: INEGI DENUE]]></description>')

    # Estilo puntos
    L.append('  <Style id="papeleria">')
    L.append('    <IconStyle>')
    L.append('      <color>FF0000FF</color>')
    L.append('      <scale>0.7</scale>')
    L.append('      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/schools.png</href></Icon>')
    L.append('    </IconStyle>')
    L.append('    <LabelStyle><scale>0</scale></LabelStyle>')
    L.append('  </Style>')

    # Estilos hexagonos
    for c in unique_counts:
        col = _kml_color(c, max_cantidad)
        L.append(f'  <Style id="hex_{c}">')
        L.append(f'    <LineStyle><color>88333333</color><width>0.4</width></LineStyle>')
        L.append(f'    <PolyStyle><color>{col}</color></PolyStyle>')
        L.append(f'  </Style>')

    # ── Carpeta: Hexagonos H3 ─────────────────────────────────────────────────
    L.append('  <Folder>')
    L.append('    <name>Hexagonos H3 (densidad)</name>')
    L.append(f'    <description><![CDATA[{len(hexagonos)} celdas H3 res.9 | ~0.1 km² c/u<br/>'
             f'<font color="#00C800">&#9632;</font> Verde = 1 papeleria &nbsp; '
             f'<font color="#FFFF00">&#9632;</font> Amarillo = densidad media &nbsp; '
             f'<font color="#FF0000">&#9632;</font> Rojo = maxima densidad<br/>'
             f'Max: {max_cantidad} papelerias/celda]]></description>')

    for h in sorted(hexagonos, key=lambda x: x["cantidad"]):
        coords = _geojson_polygon_to_kml_coords(h["geom"])
        if not coords:
            continue
        pct = round(h["intensidad"] * 100, 1)
        desc = (
            f"Papelerias en celda: <b>{h['cantidad']}</b><br/>"
            f"% del total zona: {pct}%<br/>"
            f"H3 index: {h['h3_index']}"
        )
        L.append('    <Placemark>')
        L.append(f'      <name>{h["cantidad"]} papeleria{"s" if h["cantidad"] != 1 else ""}</name>')
        L.append(f'      <description><![CDATA[{desc}]]></description>')
        L.append(f'      <styleUrl>#hex_{h["cantidad"]}</styleUrl>')
        L.append('      <Polygon><tessellate>1</tessellate>')
        L.append('        <outerBoundaryIs><LinearRing>')
        L.append(f'          <coordinates>{coords}</coordinates>')
        L.append('        </LinearRing></outerBoundaryIs>')
        L.append('      </Polygon>')
        L.append('    </Placemark>')

    L.append('  </Folder>')

    # ── Carpeta: Puntos individuales ──────────────────────────────────────────
    L.append('  <Folder>')
    L.append(f'  <name>Papelerias ({len(puntos)})</name>')
    L.append('  <description>Establecimientos individuales. Fuente: INEGI DENUE via API.</description>')

    for p in puntos:
        desc = (
            f"Clase: {escape(p['clase_actividad'])}<br/>"
            f"SCIAN: {escape(p['codigo_scian'])}<br/>"
            f"Personal: {escape(p['estrato_personal'])}<br/>"
            f"Colonia: {escape(p['colonia'])}<br/>"
            f"Municipio: {escape(p['municipio'])}"
        )
        L.append('    <Placemark>')
        L.append(f'      <name>{escape(p["nombre"])}</name>')
        L.append(f'      <description><![CDATA[{desc}]]></description>')
        L.append('      <styleUrl>#papeleria</styleUrl>')
        L.append('      <Point>')
        L.append(f'        <coordinates>{p["lon"]:.6f},{p["lat"]:.6f},0</coordinates>')
        L.append('      </Point>')
        L.append('    </Placemark>')

    L.append('  </Folder>')
    L.append('</Document>')
    L.append('</kml>')

    return '\n'.join(L)


def save_kmz(kml_content: str, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', kml_content.encode('utf-8'))


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="KMZ papelerias Ecatepec via API")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[2] / "resultados" / "ecatepec_papelerias.kmz"),
    )
    args = parser.parse_args()

    print(f"API: {API_BASE}")

    print("1/4 -> Login...")
    token = login()
    print("     [OK] JWT obtenido")

    print("2/4 -> Consultando hexagonos H3 (concentracion-comercial)...")
    hexagonos, total = get_hexagonos(token)
    max_c = max((h["cantidad"] for h in hexagonos), default=0)
    print(f"     [OK] {len(hexagonos)} celdas H3 | total {total} establecimientos | max {max_c}/celda")

    print("3/4 -> Consultando papelerias individuales (establecimientos)...")
    puntos = get_puntos(token)
    print(f"     [OK] {len(puntos)} papelerias con coordenadas")

    print("4/4 -> Generando KMZ...")
    kml = generate_kml(hexagonos, puntos, total)
    save_kmz(kml, args.output)

    print(f"\n[OK] {args.output}")
    print(f"     Abre con Google Earth o importa en Google My Maps")
    print(f"     {len(puntos)} puntos | {len(hexagonos)} hexagonos")
    print(f"     Verde = baja densidad | Amarillo = media | Rojo = alta densidad")


if __name__ == "__main__":
    main()
