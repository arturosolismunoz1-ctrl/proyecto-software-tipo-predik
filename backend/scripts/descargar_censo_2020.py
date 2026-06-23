"""
Descarga automatica de "Principales resultados por AGEB y manzana urbana 2020"
para los 32 estados de Mexico desde INEGI.

Los archivos se guardan en data/censo_2020/ y se descomprimen automaticamente.
El script es reanudable: si el CSV ya existe, omite ese estado.

Uso:
    python backend/scripts/descargar_censo_2020.py
    python backend/scripts/descargar_censo_2020.py --estados 09,14,15
    python backend/scripts/descargar_censo_2020.py --forzar   # re-descarga aunque ya exista
"""
import argparse
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ESTADOS = {
    "01": "Aguascalientes",
    "02": "Baja California",
    "03": "Baja California Sur",
    "04": "Campeche",
    "05": "Coahuila de Zaragoza",
    "06": "Colima",
    "07": "Chiapas",
    "08": "Chihuahua",
    "09": "Ciudad de Mexico",
    "10": "Durango",
    "11": "Guanajuato",
    "12": "Guerrero",
    "13": "Hidalgo",
    "14": "Jalisco",
    "15": "Mexico",
    "16": "Michoacan de Ocampo",
    "17": "Morelos",
    "18": "Nayarit",
    "19": "Nuevo Leon",
    "20": "Oaxaca",
    "21": "Puebla",
    "22": "Queretaro",
    "23": "Quintana Roo",
    "24": "San Luis Potosi",
    "25": "Sinaloa",
    "26": "Sonora",
    "27": "Tabasco",
    "28": "Tamaulipas",
    "29": "Tlaxcala",
    "30": "Veracruz de Ignacio de la Llave",
    "31": "Yucatan",
    "32": "Zacatecas",
}

# URL directa de INEGI para cada estado
# Patron: RESAGEBURB_{clave}_2020_csv.zip
_URL_BASE = (
    "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/"
    "microdatos/ageb_manzana/RESAGEBURB_{clave}_2020_csv.zip"
)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "censo_2020"


def _progress(downloaded: int, total: int, nombre: str) -> None:
    if total > 0:
        pct = downloaded * 100 // total
        mb = downloaded / 1_048_576
        print(f"\r  {nombre}: {mb:.1f} MB  ({pct}%)", end="", flush=True)


def descargar_estado(clave: str, nombre: str, forzar: bool = False) -> bool:
    """
    Descarga y descomprime el CSV de un estado.
    Retorna True si se descargo exitosamente (o ya existia).
    """
    zip_path = OUTPUT_DIR / f"RESAGEBURB_{clave}_2020_csv.zip"
    csv_name_upper = f"RESAGEBURB_{clave}_2020.CSV"
    csv_name_lower = f"RESAGEBURB_{clave}_2020.csv"
    csv_path_upper = OUTPUT_DIR / csv_name_upper
    csv_path_lower = OUTPUT_DIR / csv_name_lower

    # Si ya existe el CSV extraido, saltar
    if not forzar and (csv_path_upper.exists() or csv_path_lower.exists()):
        existente = csv_path_upper if csv_path_upper.exists() else csv_path_lower
        size_mb = existente.stat().st_size / 1_048_576
        print(f"  [{clave}] {nombre:<35} ya existe ({size_mb:.1f} MB) — omitido")
        return True

    url = _URL_BASE.format(clave=clave)
    print(f"  [{clave}] {nombre:<35} descargando...", end="", flush=True)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "predik-geo/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536
            with open(zip_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    _progress(downloaded, total, nombre[:20])

        print()  # nueva linea tras la barra de progreso

        # Extraer ZIP
        with zipfile.ZipFile(zip_path, "r") as zf:
            nombres = zf.namelist()
            csv_en_zip = [n for n in nombres if n.upper().endswith(".CSV")]
            zf.extractall(OUTPUT_DIR)

        zip_path.unlink()  # borrar ZIP despues de extraer

        extraidos = [OUTPUT_DIR / n for n in csv_en_zip]
        sizes = [f"{p.stat().st_size/1_048_576:.1f} MB" for p in extraidos if p.exists()]
        print(f"       -> {', '.join(sizes) or 'extraido'}")
        return True

    except Exception as e:
        print(f"\n  [!] Error {clave} {nombre}: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(description="Descarga Censo 2020 AGEB - 32 estados")
    parser.add_argument("--estados", type=str, help="Claves separadas por coma. Ej: 09,14,15")
    parser.add_argument("--forzar", action="store_true", help="Re-descargar aunque ya exista")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    estados_a_procesar = sorted(ESTADOS.keys())
    if args.estados:
        estados_a_procesar = [e.strip().zfill(2) for e in args.estados.split(",")]

    print()
    print("=" * 65)
    print("  DESCARGA: Censo 2020 — AGEB y manzana urbana")
    print(f"  Destino:  data/censo_2020/")
    print(f"  Estados:  {len(estados_a_procesar)}")
    print("=" * 65)
    print()

    ok = 0
    errores = []
    t0 = time.time()

    for clave in estados_a_procesar:
        nombre = ESTADOS.get(clave, f"Estado {clave}")
        exito = descargar_estado(clave, nombre, forzar=args.forzar)
        if exito:
            ok += 1
        else:
            errores.append(f"{clave} {nombre}")
        time.sleep(0.5)  # cortesia con INEGI

    elapsed = time.time() - t0
    print()
    print("-" * 65)
    print(f"  Completados: {ok}/{len(estados_a_procesar)} estados en {elapsed/60:.1f} min")
    if errores:
        print(f"  Errores ({len(errores)}):")
        for e in errores:
            print(f"    - {e}")
    print("=" * 65)
    print()
    print("  Siguiente paso — cargar a la base de datos:")
    print("  python backend/scripts/load_censo_2020.py --dir data/censo_2020/")
    print()


if __name__ == "__main__":
    main()
