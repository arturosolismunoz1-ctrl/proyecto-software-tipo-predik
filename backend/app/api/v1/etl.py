import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.api.v1.admin import require_admin
from app.deps import get_db
from app.etl.denue import DenueETL

router = APIRouter()

_ETL_REGISTRY: Dict[str, Any] = {
    "inegi_denue": DenueETL,
}

_ESTADOS = {
    "01":"Aguascalientes","02":"Baja California","03":"Baja California Sur",
    "04":"Campeche","05":"Coahuila","06":"Colima","07":"Chiapas",
    "08":"Chihuahua","09":"Ciudad de Mexico","10":"Durango",
    "11":"Guanajuato","12":"Guerrero","13":"Hidalgo","14":"Jalisco",
    "15":"Mexico","16":"Michoacan","17":"Morelos","18":"Nayarit",
    "19":"Nuevo Leon","20":"Oaxaca","21":"Puebla","22":"Queretaro",
    "23":"Quintana Roo","24":"San Luis Potosi","25":"Sinaloa",
    "26":"Sonora","27":"Tabasco","28":"Tamaulipas","29":"Tlaxcala",
    "30":"Veracruz","31":"Yucatan","32":"Zacatecas",
}
PAGE_SIZE = 2500


class ETLRunRequest(BaseModel):
    estado: str = "09"
    municipio: Optional[str] = None  # 3-digit code, e.g. "033" for Ecatepec
    keyword: str = ""
    max_records: int = 100
    polygon: Optional[Dict[str, Any]] = None


class ETLRunResult(BaseModel):
    source: str
    extracted: int
    loaded: int
    aggregated: int


@router.post("/etl/{source}/run", response_model=ETLRunResult)
async def run_etl(
    source: str,
    req: ETLRunRequest = ETLRunRequest(),
    db=Depends(get_db),
    _current_user: dict = Depends(require_admin),
) -> ETLRunResult:
    etl_cls = _ETL_REGISTRY.get(source)
    if etl_cls is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"ETL source '{source}' not found")

    etl = etl_cls()
    run_params: Dict[str, Any] = {
        "estado": req.estado,
        "keyword": req.keyword,
        "max_records": req.max_records,
        "polygon": req.polygon,
    }
    if req.municipio is not None:
        run_params["municipio"] = req.municipio

    stats = await etl.run(db, **run_params)
    return ETLRunResult(source=source, **stats)


# ── ETL Maestro paginado ───────────────────────────────────────────────────────

class ETLMaestroRequest(BaseModel):
    estados: Optional[List[str]] = None   # None = todos los 32 estados
    keyword: str = ""


class ETLMaestroEstadoResult(BaseModel):
    estado: str
    nombre: str
    extraidos: int
    cargados: int
    paginas: int


class ETLMaestroResult(BaseModel):
    total_extraidos: int
    total_estados: int
    detalle: List[ETLMaestroEstadoResult]


_SECTORES_DENUE = [
    "comercio", "restaurante", "alimentos", "servicio", "salud",
    "educacion", "transporte", "construccion", "manufactura", "inmobiliario",
    "hotel", "banco", "recreacion", "tecnologia", "agropecuario",
    "taller", "belleza", "gasolinera", "farmacia", "medico",
]


async def _denue_get_page(url: str) -> list:
    import json
    import urllib.request as _urllib
    req = _urllib.Request(url, headers={"User-Agent": "predik-geo/1.0"})
    try:
        raw = await asyncio.to_thread(lambda r=req: _urllib.urlopen(r, timeout=30).read())
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def _descargar_estado_paginado(
    db, etl: DenueETL, estado: str, keyword: str
) -> ETLMaestroEstadoResult:
    """
    Descarga todos los establecimientos de un estado.
    Si keyword está vacío, itera sobre SECTORES_DENUE para cubrir todos los giros.
    La API INEGI no soporta wildcard '.' (normalizado por RFC en clientes HTTP).
    """
    import os
    from app.connectors.inegi.denue import _BASE_URL, _item_to_geo_feature

    token = os.getenv("INEGI_DENUE_TOKEN", "")
    total_extraidos = 0
    total_cargados = 0
    total_paginas = 0

    sectores = [keyword] if keyword else _SECTORES_DENUE

    for sector in sectores:
        pagina = 0
        while True:
            inicio = pagina * PAGE_SIZE
            fin = inicio + PAGE_SIZE
            url = f"{_BASE_URL}/BuscarEntidad/{sector}/{estado}/{inicio}/{fin}/{token}"

            data = await _denue_get_page(url)
            if not data:
                break

            features = [f for item in data if (f := _item_to_geo_feature(item)) is not None]
            if features:
                total_cargados += etl.load_raw(features, db)
                total_extraidos += len(features)

            pagina += 1
            total_paginas += 1
            if len(data) < PAGE_SIZE:
                break

            await asyncio.sleep(0.3)

    return ETLMaestroEstadoResult(
        estado=estado,
        nombre=_ESTADOS.get(estado, estado),
        extraidos=total_extraidos,
        cargados=total_cargados,
        paginas=total_paginas,
    )


@router.post("/etl/maestro/run", response_model=ETLMaestroResult)
async def run_etl_maestro(
    req: ETLMaestroRequest = ETLMaestroRequest(),
    db=Depends(get_db),
    _current_user: dict = Depends(require_admin),
) -> ETLMaestroResult:
    """
    Descarga TODOS los establecimientos de Mexico desde INEGI DENUE,
    paginando de 2,500 en 2,500 por estado.

    Sin estados especificados descarga los 32 estados (~5.5M registros, 2-4 horas).
    Para prueba rapida: estados=["09","14","15"]
    """
    estados_a_procesar = sorted(
        req.estados if req.estados else list(_ESTADOS.keys())
    )

    etl = DenueETL()
    detalle = []
    total = 0

    for estado in estados_a_procesar:
        resultado = await _descargar_estado_paginado(
            db, etl, estado.zfill(2), req.keyword
        )
        detalle.append(resultado)
        total += resultado.extraidos

    return ETLMaestroResult(
        total_extraidos=total,
        total_estados=len(detalle),
        detalle=detalle,
    )
