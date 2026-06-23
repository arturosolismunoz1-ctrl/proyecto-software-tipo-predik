"""
Prueba funcional — Guadalajara, Jalisco: McDonald's vs Burger King.

Flujo completo via API:
  1. Login
  2. ETL McDonald's  (keyword="mcdonald",    estado=14)
  3. ETL Burger King (keyword="burger king", estado=14)
  4. Concentración comercial -> hexagonos H3
  5. Establecimientos McDonald's -> puntos rojos
  6. Establecimientos Burger King -> puntos verdes
  7. Calcula oportunidad por hexagono
  8. Genera KMZ

Uso:
  python backend/scripts/prueba_guadalajara_fastfood.py
  python backend/scripts/prueba_guadalajara_fastfood.py --skip-etl
"""
import argparse
import json
import os
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import requests

# h3 para calcular en que celda cae cada punto (calculo local, no DB)
import h3

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")
EMAIL    = os.getenv("PREDIK_EMAIL", "admin@predik.local")
PASSWORD = os.getenv("PREDIK_PASSWORD", "dev_password_admin")

# Bounding box de Guadalajara (municipio + area periferica cercana)
GDL_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [-103.45, 20.57],
        [-103.22, 20.57],
        [-103.22, 20.77],
        [-103.45, 20.77],
        [-103.45, 20.57],
    ]],
}

H3_RESOLUTION = 9


# ── Auth ───────────────────────────────────────────────────────────────────────

def login() -> str:
    r = requests.post(f"{API_BASE}/auth/login",
                      json={"email": EMAIL, "password": PASSWORD}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


# ── ETL ────────────────────────────────────────────────────────────────────────

def run_etl(token: str, keyword: str, label: str) -> dict:
    print(f"   ETL '{label}' (keyword={keyword}, estado=14, max=2500)...")
    r = requests.post(
        f"{API_BASE}/admin/etl/inegi_denue/run",
        json={
            "estado": "14",
            "keyword": keyword,
            "max_records": 2500,
            "h3_resolution": H3_RESOLUTION,
            "polygon": GDL_POLYGON,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=180,
    )
    if r.status_code != 200:
        print(f"   [!] ETL retorno {r.status_code}: {r.text[:200]}")
        return {}
    d = r.json()
    print(f"   [OK] {d.get('extracted',0)} extraidos | "
          f"{d.get('loaded',0)} en raw_data | "
          f"{d.get('aggregated',0)} celdas H3")
    return d


# ── Consultas zona ─────────────────────────────────────────────────────────────

def get_hexagonos(token: str) -> tuple[list[dict], int]:
    r = requests.post(
        f"{API_BASE}/zona/concentracion-comercial",
        json={"geometry": GDL_POLYGON},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if r.status_code == 404:
        print("   [!] Sin cobertura en cubo (ETL no cargo datos)")
        return [], 0
    r.raise_for_status()
    d = r.json()
    return d["celdas_heatmap"], d["total_establecimientos"]


def get_puntos(token: str, keyword: str) -> list[dict]:
    r = requests.post(
        f"{API_BASE}/zona/establecimientos",
        json={"geometry": GDL_POLYGON, "keyword": keyword},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["establecimientos"]


# ── Oportunidad ────────────────────────────────────────────────────────────────

def clasificar_oportunidad(
    hexagonos: list[dict],
    mc_puntos: list[dict],
    bk_puntos: list[dict],
) -> list[dict]:
    """
    Agrega campo 'oportunidad' a cada hexagono.

    Logica:
      - Calcula que celdas H3 tienen McDonald's y/o Burger King
      - Clasifica cada celda segun densidad comercial + presencia de cadenas

    Niveles:
      ALTA         Verde oscuro  — alta densidad, ninguna cadena
      MEDIA_ALTA   Verde claro   — densidad media-alta, ninguna cadena
      MEDIA        Amarillo      — densidad media O solo una cadena
      BAJA         Gris          — baja densidad, sin cadenas
      CON_MC       Naranja       — tiene McDonald's, sin Burger King
      CON_BK       Azul          — tiene Burger King, sin McDonald's
      SATURADA     Rojo          — tiene ambas cadenas
    """
    mc_cells = {
        h3.latlng_to_cell(p["lat"], p["lon"], H3_RESOLUTION)
        for p in mc_puntos
        if p.get("lat") and p.get("lon")
    }
    bk_cells = {
        h3.latlng_to_cell(p["lat"], p["lon"], H3_RESOLUTION)
        for p in bk_puntos
        if p.get("lat") and p.get("lon")
    }

    intensidades = sorted(h["intensidad"] for h in hexagonos)
    n = len(intensidades)
    q33 = intensidades[n // 3] if n > 2 else 0
    q66 = intensidades[2 * n // 3] if n > 2 else 0

    result = []
    for h in hexagonos:
        has_mc = h["h3_index"] in mc_cells
        has_bk = h["h3_index"] in bk_cells

        if has_mc and has_bk:
            nivel = "SATURADA"
        elif has_mc and not has_bk:
            nivel = "CON_MC"
        elif has_bk and not has_mc:
            nivel = "CON_BK"
        else:
            # Sin cadena — clasificar por densidad
            if h["intensidad"] >= q66:
                nivel = "ALTA"
            elif h["intensidad"] >= q33:
                nivel = "MEDIA_ALTA"
            else:
                nivel = "BAJA"

        result.append({**h, "oportunidad": nivel})
    return result


# ── Colores KML ────────────────────────────────────────────────────────────────

_OPORTUNIDAD_COLOR = {
    # AABBGGRR
    "ALTA":       "CC00C800",   # verde oscuro
    "MEDIA_ALTA": "CC44E844",   # verde claro
    "MEDIA":      "CC00DDDD",   # amarillo
    "BAJA":       "CC999999",   # gris
    "CON_MC":     "CC0066FF",   # naranja (tiene MC, oportunidad para BK)
    "CON_BK":     "CCFF8800",   # azul (tiene BK, oportunidad para MC)
    "SATURADA":   "CC0000CC",   # rojo
}

_OPORTUNIDAD_LABEL = {
    "ALTA":       "ALTA OPORTUNIDAD",
    "MEDIA_ALTA": "OPORTUNIDAD MEDIA-ALTA",
    "MEDIA":      "OPORTUNIDAD MEDIA",
    "BAJA":       "BAJA ACTIVIDAD",
    "CON_MC":     "YA TIENE McDONALD'S",
    "CON_BK":     "YA TIENE BURGER KING",
    "SATURADA":   "SATURADA (ambas cadenas)",
}


# ── KML ────────────────────────────────────────────────────────────────────────

def _geojson_to_kml_coords(geom_str: str) -> str:
    geom = json.loads(geom_str)
    if geom["type"] == "Polygon":
        ring = geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        ring = geom["coordinates"][0][0]
    else:
        return ""
    return " ".join(f"{c[0]:.6f},{c[1]:.6f},0" for c in ring)


def generate_kml(
    hexagonos: list[dict],
    mc_puntos: list[dict],
    bk_puntos: list[dict],
) -> str:
    niveles_usados = sorted(set(h["oportunidad"] for h in hexagonos))

    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>')
    L.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
    L.append('<Document>')
    L.append("  <name>McDonald's vs Burger King — Guadalajara, Jalisco</name>")
    n_alta = sum(1 for h in hexagonos if h["oportunidad"] in ("ALTA", "MEDIA_ALTA"))
    L.append(f'  <description><![CDATA['
             f"<b>McDonald's:</b> {len(mc_puntos)} sucursales &nbsp;|&nbsp; "
             f"<b>Burger King:</b> {len(bk_puntos)} sucursales<br/>"
             f"{len(hexagonos)} celdas H3 analizadas &nbsp;|&nbsp; "
             f"<b>{n_alta} zonas de oportunidad</b> detectadas<br/>"
             f"Guadalajara, Jalisco — Fuente: INEGI DENUE"
             f']]></description>')

    # Estilos puntos
    for sid, color, icon in [
        ("mcdonalds", "FF0000FF",  # rojo KML
         "http://maps.google.com/mapfiles/kml/paddle/red-circle.png"),
        ("burgerking", "FF00FF00",  # verde KML
         "http://maps.google.com/mapfiles/kml/paddle/grn-circle.png"),
    ]:
        L.append(f'  <Style id="{sid}">')
        L.append(f'    <IconStyle><color>{color}</color><scale>0.9</scale>')
        L.append(f'      <Icon><href>{icon}</href></Icon>')
        L.append(f'    </IconStyle>')
        L.append(f'    <LabelStyle><scale>0</scale></LabelStyle>')
        L.append(f'  </Style>')

    # Estilos hexagonos
    for nivel in niveles_usados:
        col = _OPORTUNIDAD_COLOR.get(nivel, "CC888888")
        L.append(f'  <Style id="hex_{nivel}">')
        L.append(f'    <LineStyle><color>88111111</color><width>0.3</width></LineStyle>')
        L.append(f'    <PolyStyle><color>{col}</color></PolyStyle>')
        L.append(f'  </Style>')

    # ── Hexagonos ─────────────────────────────────────────────────────────────
    L.append('  <Folder>')
    L.append('    <name>Hexagonos H3 — Oportunidad</name>')

    leyenda = "<br/>".join(
        f'<font color="#{_OPORTUNIDAD_COLOR.get(n,"888888")[6:]}{_OPORTUNIDAD_COLOR.get(n,"888888")[4:6]}{_OPORTUNIDAD_COLOR.get(n,"888888")[2:4]}">&#9632;</font> {_OPORTUNIDAD_LABEL.get(n,n)}'
        for n in ["ALTA", "MEDIA_ALTA", "BAJA", "CON_MC", "CON_BK", "SATURADA"]
    )
    L.append(f'    <description><![CDATA[{leyenda}]]></description>')

    for h in sorted(hexagonos, key=lambda x: x["intensidad"]):
        coords = _geojson_to_kml_coords(h["geom"])
        if not coords:
            continue
        label = _OPORTUNIDAD_LABEL.get(h["oportunidad"], h["oportunidad"])
        desc = (
            f"Clasificacion: <b>{label}</b><br/>"
            f"Establecimientos en celda: {h['cantidad']}<br/>"
            f"Intensidad: {round(h['intensidad']*100,2)}%<br/>"
            f"H3 index: {h['h3_index']}"
        )
        L.append('    <Placemark>')
        L.append(f'      <name>{label}</name>')
        L.append(f'      <description><![CDATA[{desc}]]></description>')
        L.append(f'      <styleUrl>#hex_{h["oportunidad"]}</styleUrl>')
        L.append('      <Polygon><tessellate>1</tessellate>')
        L.append('        <outerBoundaryIs><LinearRing>')
        L.append(f'          <coordinates>{coords}</coordinates>')
        L.append('        </LinearRing></outerBoundaryIs>')
        L.append('      </Polygon>')
        L.append('    </Placemark>')

    L.append('  </Folder>')

    # ── McDonald's ────────────────────────────────────────────────────────────
    L.append('  <Folder>')
    L.append(f"  <name>McDonald's ({len(mc_puntos)})</name>")
    L.append('  <description>Sucursales McDonald\'s en Guadalajara. Fuente: INEGI DENUE.</description>')
    for p in mc_puntos:
        desc = (
            f"Clase: {escape(p['clase_actividad'])}<br/>"
            f"Personal: {escape(p['estrato_personal'])}<br/>"
            f"Colonia: {escape(p['colonia'])}"
        )
        L.append('    <Placemark>')
        L.append(f"      <name>{escape(p['nombre'])}</name>")
        L.append(f'      <description><![CDATA[{desc}]]></description>')
        L.append('      <styleUrl>#mcdonalds</styleUrl>')
        L.append('      <Point>')
        L.append(f'        <coordinates>{p["lon"]:.6f},{p["lat"]:.6f},0</coordinates>')
        L.append('      </Point>')
        L.append('    </Placemark>')
    L.append('  </Folder>')

    # ── Burger King ───────────────────────────────────────────────────────────
    L.append('  <Folder>')
    L.append(f'  <name>Burger King ({len(bk_puntos)})</name>')
    L.append('  <description>Sucursales Burger King en Guadalajara. Fuente: INEGI DENUE.</description>')
    for p in bk_puntos:
        desc = (
            f"Clase: {escape(p['clase_actividad'])}<br/>"
            f"Personal: {escape(p['estrato_personal'])}<br/>"
            f"Colonia: {escape(p['colonia'])}"
        )
        L.append('    <Placemark>')
        L.append(f"      <name>{escape(p['nombre'])}</name>")
        L.append(f'      <description><![CDATA[{desc}]]></description>')
        L.append('      <styleUrl>#burgerking</styleUrl>')
        L.append('      <Point>')
        L.append(f'        <coordinates>{p["lon"]:.6f},{p["lat"]:.6f},0</coordinates>')
        L.append('      </Point>')
        L.append('    </Placemark>')
    L.append('  </Folder>')

    L.append('</Document>')
    L.append('</kml>')
    return '\n'.join(L)


def save_kmz(kml: str, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', kml.encode('utf-8'))


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(
        Path(__file__).resolve().parents[2] / "resultados" / "guadalajara_fastfood.kmz"
    ))
    parser.add_argument("--skip-etl", action="store_true")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  McDONALD'S vs BURGER KING — Guadalajara, Jalisco")
    print("  API:", API_BASE)
    print("=" * 60)

    print("\n1/5 -> Login...")
    token = login()
    print("     [OK]")

    if not args.skip_etl:
        print("\n2/5 -> ETL cadenas de comida rapida...")
        run_etl(token, "mc donalds", "McDonald's")
        run_etl(token, "burger king", "Burger King")
    else:
        print("\n2/5 -> [ETL omitido]")

    print("\n3/5 -> Hexagonos H3 (concentracion-comercial)...")
    hexagonos_raw, total = get_hexagonos(token)
    print(f"     [OK] {len(hexagonos_raw)} celdas H3 | {total} establecimientos")

    print("\n4/5 -> Puntos individuales...")
    mc_puntos = get_puntos(token, "mc donalds")
    bk_puntos = get_puntos(token, "burger king")
    print(f"     [OK] McDonald's: {len(mc_puntos)} | Burger King: {len(bk_puntos)}")

    print("\n5/5 -> Calculando oportunidad y generando KMZ...")
    hexagonos = clasificar_oportunidad(hexagonos_raw, mc_puntos, bk_puntos)

    conteo = {}
    for h in hexagonos:
        conteo[h["oportunidad"]] = conteo.get(h["oportunidad"], 0) + 1
    for nivel, n in sorted(conteo.items()):
        print(f"     {_OPORTUNIDAD_LABEL.get(nivel, nivel):35s}: {n} celdas")

    kml = generate_kml(hexagonos, mc_puntos, bk_puntos)
    save_kmz(kml, args.output)

    print(f"\n[OK] {args.output}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
