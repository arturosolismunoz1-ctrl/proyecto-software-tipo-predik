"""
Catalogo de entidades federativas y municipios de Mexico (INEGI).

GET /api/v1/catalogo/estados          -> lista de 32 estados con su clave INEGI
GET /api/v1/catalogo/municipios/{clave_estado}  -> municipios del estado

Estos datos alimentan los dropdowns del frontend para que el usuario
seleccione estado -> municipio antes de lanzar una busqueda.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.deps import get_db

router = APIRouter()


class Estado(BaseModel):
    clave: str          # "14"
    nombre: str         # "Jalisco"
    abreviatura: str    # "JAL"


class Municipio(BaseModel):
    clave: str          # "039"
    nombre: str         # "Guadalajara"
    clave_estado: str   # "14"


class MunicipioBbox(BaseModel):
    nombre: str
    clave_estado: str
    clave_mun: str
    minx: float
    miny: float
    maxx: float
    maxy: float
    center_lat: float
    center_lng: float


# ── Catálogo estático INEGI ────────────────────────────────────────────────────

_ESTADOS: List[Estado] = [
    Estado(clave="01", nombre="Aguascalientes",             abreviatura="AGS"),
    Estado(clave="02", nombre="Baja California",            abreviatura="BC"),
    Estado(clave="03", nombre="Baja California Sur",        abreviatura="BCS"),
    Estado(clave="04", nombre="Campeche",                   abreviatura="CAMP"),
    Estado(clave="05", nombre="Coahuila de Zaragoza",       abreviatura="COAH"),
    Estado(clave="06", nombre="Colima",                     abreviatura="COL"),
    Estado(clave="07", nombre="Chiapas",                    abreviatura="CHIS"),
    Estado(clave="08", nombre="Chihuahua",                  abreviatura="CHIH"),
    Estado(clave="09", nombre="Ciudad de Mexico",           abreviatura="CDMX"),
    Estado(clave="10", nombre="Durango",                    abreviatura="DGO"),
    Estado(clave="11", nombre="Guanajuato",                 abreviatura="GTO"),
    Estado(clave="12", nombre="Guerrero",                   abreviatura="GRO"),
    Estado(clave="13", nombre="Hidalgo",                    abreviatura="HGO"),
    Estado(clave="14", nombre="Jalisco",                    abreviatura="JAL"),
    Estado(clave="15", nombre="Mexico",                     abreviatura="MEX"),
    Estado(clave="16", nombre="Michoacan de Ocampo",        abreviatura="MICH"),
    Estado(clave="17", nombre="Morelos",                    abreviatura="MOR"),
    Estado(clave="18", nombre="Nayarit",                    abreviatura="NAY"),
    Estado(clave="19", nombre="Nuevo Leon",                 abreviatura="NL"),
    Estado(clave="20", nombre="Oaxaca",                     abreviatura="OAX"),
    Estado(clave="21", nombre="Puebla",                     abreviatura="PUE"),
    Estado(clave="22", nombre="Queretaro",                  abreviatura="QRO"),
    Estado(clave="23", nombre="Quintana Roo",               abreviatura="QROO"),
    Estado(clave="24", nombre="San Luis Potosi",            abreviatura="SLP"),
    Estado(clave="25", nombre="Sinaloa",                    abreviatura="SIN"),
    Estado(clave="26", nombre="Sonora",                     abreviatura="SON"),
    Estado(clave="27", nombre="Tabasco",                    abreviatura="TAB"),
    Estado(clave="28", nombre="Tamaulipas",                 abreviatura="TAMPS"),
    Estado(clave="29", nombre="Tlaxcala",                   abreviatura="TLAX"),
    Estado(clave="30", nombre="Veracruz de Ignacio de la Llave", abreviatura="VER"),
    Estado(clave="31", nombre="Yucatan",                    abreviatura="YUC"),
    Estado(clave="32", nombre="Zacatecas",                  abreviatura="ZAC"),
]

# Municipios de los estados mas consultados.
# Fuente: Marco Geoestadistico INEGI 2023.
# Se amplian al cargar el shapefile MGN completo.
_MUNICIPIOS: List[Municipio] = [
    # CDMX (09)
    Municipio(clave="002", nombre="Azcapotzalco",           clave_estado="09"),
    Municipio(clave="003", nombre="Coyoacan",               clave_estado="09"),
    Municipio(clave="004", nombre="Cuajimalpa de Morelos",  clave_estado="09"),
    Municipio(clave="005", nombre="Gustavo A. Madero",      clave_estado="09"),
    Municipio(clave="006", nombre="Iztacalco",              clave_estado="09"),
    Municipio(clave="007", nombre="Iztapalapa",             clave_estado="09"),
    Municipio(clave="008", nombre="La Magdalena Contreras", clave_estado="09"),
    Municipio(clave="009", nombre="Milpa Alta",             clave_estado="09"),
    Municipio(clave="010", nombre="Alvaro Obregon",         clave_estado="09"),
    Municipio(clave="011", nombre="Tlahuac",                clave_estado="09"),
    Municipio(clave="012", nombre="Tlalpan",                clave_estado="09"),
    Municipio(clave="013", nombre="Xochimilco",             clave_estado="09"),
    Municipio(clave="014", nombre="Benito Juarez",          clave_estado="09"),
    Municipio(clave="015", nombre="Cuauhtemoc",             clave_estado="09"),
    Municipio(clave="016", nombre="Miguel Hidalgo",         clave_estado="09"),
    Municipio(clave="017", nombre="Venustiano Carranza",    clave_estado="09"),
    # Jalisco (14)
    Municipio(clave="039", nombre="Guadalajara",            clave_estado="14"),
    Municipio(clave="098", nombre="Tlaquepaque",            clave_estado="14"),
    Municipio(clave="101", nombre="Tonala",                 clave_estado="14"),
    Municipio(clave="120", nombre="Zapopan",                clave_estado="14"),
    Municipio(clave="097", nombre="Tlajomulco de Zuniga",   clave_estado="14"),
    Municipio(clave="055", nombre="Lagos de Moreno",        clave_estado="14"),
    Municipio(clave="067", nombre="Puerto Vallarta",        clave_estado="14"),
    # Estado de Mexico (15)
    Municipio(clave="033", nombre="Ecatepec de Morelos",    clave_estado="15"),
    Municipio(clave="106", nombre="Toluca",                 clave_estado="15"),
    Municipio(clave="057", nombre="Naucalpan de Juarez",    clave_estado="15"),
    Municipio(clave="058", nombre="Nezahualcoyotl",         clave_estado="15"),
    Municipio(clave="099", nombre="Tlalnepantla de Baz",    clave_estado="15"),
    Municipio(clave="122", nombre="Zinacantepec",           clave_estado="15"),
    # Nuevo Leon (19)
    Municipio(clave="039", nombre="Monterrey",              clave_estado="19"),
    Municipio(clave="006", nombre="Apodaca",                clave_estado="19"),
    Municipio(clave="018", nombre="Escobedo",               clave_estado="19"),
    Municipio(clave="021", nombre="Guadalupe",              clave_estado="19"),
    Municipio(clave="046", nombre="San Nicolas de los Garza", clave_estado="19"),
    Municipio(clave="048", nombre="San Pedro Garza Garcia", clave_estado="19"),
    # Puebla (21)
    Municipio(clave="114", nombre="Puebla",                 clave_estado="21"),
    Municipio(clave="132", nombre="San Andres Cholula",     clave_estado="21"),
    # Veracruz (30)
    Municipio(clave="193", nombre="Veracruz",               clave_estado="30"),
    Municipio(clave="087", nombre="Xalapa",                 clave_estado="30"),
    Municipio(clave="118", nombre="Orizaba",                clave_estado="30"),
    # Yucatan (31)
    Municipio(clave="050", nombre="Merida",                 clave_estado="31"),
    # Queretaro (22)
    Municipio(clave="014", nombre="Queretaro",              clave_estado="22"),
    # Guanajuato (11)
    Municipio(clave="020", nombre="Leon",                   clave_estado="11"),
    Municipio(clave="007", nombre="Celaya",                 clave_estado="11"),
    Municipio(clave="024", nombre="Salamanca",              clave_estado="11"),
]

_ESTADOS_IDX = {e.clave: e for e in _ESTADOS}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/estados", response_model=List[Estado], summary="Lista de estados de Mexico")
def listar_estados():
    return _ESTADOS


@router.get(
    "/municipios/{clave_estado}",
    response_model=List[Municipio],
    summary="Municipios de un estado",
)
def listar_municipios(clave_estado: str):
    clave = clave_estado.zfill(2)
    if clave not in _ESTADOS_IDX:
        raise HTTPException(status_code=404, detail=f"Estado '{clave_estado}' no encontrado")
    resultado = [m for m in _MUNICIPIOS if m.clave_estado == clave]
    return resultado


@router.get(
    "/municipio-bbox/{clave_estado}/{clave_mun}",
    response_model=MunicipioBbox,
    summary="Bounding box de un municipio (desde AGEBs MGN)",
)
def municipio_bbox(
    clave_estado: str,
    clave_mun: str,
    db: Session = Depends(get_db),
):
    ent = clave_estado.zfill(2)
    mun = clave_mun.zfill(3)

    row = db.execute(
        text("""
            SELECT
                MAX(nom_mun) AS nombre,
                ST_XMin(ST_Extent(geom)) AS minx,
                ST_YMin(ST_Extent(geom)) AS miny,
                ST_XMax(ST_Extent(geom)) AS maxx,
                ST_YMax(ST_Extent(geom)) AS maxy
            FROM raw_data.ageb_geometries
            WHERE clave_ent = :ent AND clave_mun = :mun
        """),
        {"ent": ent, "mun": mun},
    ).fetchone()

    if not row or row.minx is None:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron AGEBs para estado={ent} municipio={mun}",
        )

    return MunicipioBbox(
        nombre=row.nombre or f"{ent}-{mun}",
        clave_estado=ent,
        clave_mun=mun,
        minx=row.minx,
        miny=row.miny,
        maxx=row.maxx,
        maxy=row.maxy,
        center_lat=(row.miny + row.maxy) / 2,
        center_lng=(row.minx + row.maxx) / 2,
    )
