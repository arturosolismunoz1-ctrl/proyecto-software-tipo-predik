# Fuentes de datos INEGI — instrucciones de descarga

Esta carpeta contiene los datos fuente que alimentan la base de datos del sistema.
Algunos se descargan automaticamente por el ETL maestro (DENUE via API).
Los datos geograficos y del censo requieren descarga manual desde INEGI.

---

## 1. Marco Geoestadistico Nacional (MGN) — GEOMETRIAS DE AGEBS

**Que es:** Polígonos exactos de todas las AGEBs, municipios y estados de Mexico.
**Para que:** Capa geografica base del mapa. Reemplaza los hexagonos H3 artificiales.
**Tamanio:** ~1.5 GB (nacional) o ~30-80 MB por estado.
**Frecuencia de actualizacion:** Anual (ultima version: MGN 2023).

**Donde descargar:**
  https://www.inegi.org.mx/temas/mg/

**Pasos:**
  1. Ir a la pagina → seccion "Descarga" → "Marco Geoestadistico 2023"
  2. Seleccionar: Shapefile → Nacional (o por estado si quieres empezar pequeño)
  3. Descargar el ZIP
  4. Descomprimir en esta carpeta: `data/mgn/`

**Estructura esperada despues de descomprimir:**
```
data/mgn/
  conjunto_de_datos/
    00ent.shp       <- Entidades federativas (32 estados)
    00mun.shp       <- Municipios (2,457 municipios)
    00a.shp         <- AGEBs urbanas (~59,000 AGEBs)
    00ra.shp        <- AGEBs rurales
    00mza.shp       <- Manzanas (muy grande, ~1.5M manzanas)
    ...
```

**Alternativa por estado** (mas ligero para empezar):
  En la misma pagina seleccionar estado por estado.
  El archivo se llama algo como `15_mex_mgn2023_integridad.zip` (Estado de Mexico).
  Descomprimir en `data/mgn/{clave_estado}/`

---

## 2. Censo de Poblacion y Vivienda 2020 — DATOS DEMOGRAFICOS POR AGEB

**Que es:** Poblacion, edad, viviendas por cada AGEB de Mexico.
**Para que:** Cruzar datos demograficos con datos comerciales (DENUE).
**Tamanio:** ~500 MB (CSV nacional) o ~5-20 MB por estado.
**Frecuencia:** Cada 10 años (proximo: 2030).

**Donde descargar:**
  https://www.inegi.org.mx/programas/ccpv/2020/#Datos

**Pasos:**
  1. Ir a la pagina → "Principales resultados por AGEB y manzana urbana"
  2. Descargar: "Resultados por entidad" (CSV) — uno por estado
     O descargar el archivo nacional si esta disponible.
  3. Guardar en: `data/censo_2020/`

**Nombre del archivo:** `RESAGEBURB_15B_2020.csv` (ejemplo Estado de Mexico)
  Donde 15 es la clave del estado.

**Codificacion:** Latin-1 (ISO-8859-1) — el script de carga ya lo maneja.

---

## 3. DENUE — DIRECTORIO NACIONAL DE UNIDADES ECONOMICAS

**Que es:** Todos los negocios de Mexico (~5.5 millones de establecimientos).
**Para que:** Datos comerciales en tiempo real y analisis de competencia.
**Frecuencia:** Actualizacion trimestral en INEGI.

**Opcion A — Descarga automatica via API (RECOMENDADA):**
  El ETL maestro descarga automaticamente por estado, paginado.
  Ejecutar: `python backend/scripts/etl_maestro.py --solo-denue`
  Tiempo estimado: 2-4 horas para los 32 estados.
  Token requerido en .env: INEGI_DENUE_TOKEN

**Opcion B — Descarga masiva (archivo CSV ~1.5 GB):**
  https://www.inegi.org.mx/app/descarga/?ti=6
  Buscar: "DENUE" → "Directorio" → descargar CSV nacional
  Guardar en: `data/denue/denue_nacional.csv`
  Luego ejecutar: `python backend/scripts/cargar_denue_csv.py`

---

## Orden de carga recomendado

```bash
# 1. Primero geografias (requiere descarga manual previa)
python backend/scripts/load_marco_geoestadistico.py

# 2. Luego demografia (requiere descarga manual previa)
python backend/scripts/load_censo_2020.py

# 3. DENUE automatico via API (no requiere descarga manual)
python backend/scripts/etl_maestro.py --solo-denue

# O todo de una vez (si ya tienes los archivos descargados):
python backend/scripts/etl_maestro.py --todo
```

---

## Estado de la base de datos

| Tabla                    | Fuente              | Registros estimados | Estado   |
|--------------------------|---------------------|---------------------|----------|
| raw_data.ageb_geometries | MGN 2023            | ~59,000 AGEBs       | Pendiente descarga |
| raw_data.ageb_demographics | Censo 2020        | ~59,000 AGEBs       | Pendiente descarga |
| raw_data.denue_establishments | DENUE API      | ~5,500,000          | Parcial (demos) |
| cube.commercial_density_h3 | ETL DENUE         | Derivado            | Parcial |
| cube.population_density_h3 | ETL Censo         | Derivado            | Pendiente |
