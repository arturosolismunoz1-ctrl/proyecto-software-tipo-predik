"""
Conector INEGI BIE — Banco de Información Económica (API v2.0).

URL confirmada (retorna 200 con token válido):
  GET {BASE}/INDICATOR/{ids}/es/{area}/false/BIE-BISE/2.0/{token}?type=json

Área:
  "00"  → Nacional (único nivel confirmado funcional con estos IDs)
  Los indicadores por entidad federativa usan IDs distintos por estado.

Token: mismo que INEGI_DENUE_TOKEN (registro único en servicios/api_indicadores.html)
"""
import json
import os
import urllib.request as ur
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector, GeoFeature

_BASE_URL = "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml"
_AREA_NACIONAL = "00"

# Mapeo estado → área BIE. Vacío = todos los estados usan datos demo por ahora.
# Poblar cuando se carguen indicadores por entidad con sus IDs específicos.
_ESTADO_A_AREA: Dict[str, str] = {}

INDICADORES: Dict[str, Dict[str, str]] = {
    "itaee": {
        "id": "452001",
        "nombre": "Actividad Económica (ITAEE)",
        "descripcion": "Índice mensual de actividad económica a nivel nacional",
        "freq_label": "Mensual",
        "unidad": "Variación porcentual",
    },
    "desocupacion": {
        "id": "444612",
        "nombre": "Tasa de Desocupación (ENOE)",
        "descripcion": "Porcentaje de la PEA que no trabajó durante la semana de referencia",
        "freq_label": "Trimestral",
        "unidad": "Porcentaje",
    },
    "empleo_formal": {
        "id": "935",
        "nombre": "Trabajadores asegurados IMSS",
        "descripcion": "Total de trabajadores registrados en el IMSS",
        "freq_label": "Mensual",
        "unidad": "Personas",
    },
    # pea (444599) devuelve HTTP 400 en BIE v2.0 — ID no disponible en este endpoint
}

# Fallback demo — valores aproximados al T1 2024 por estado
_DEMO: Dict[str, Dict[str, Any]] = {
    "01": {"itaee": 1.8, "desocupacion": 2.5, "empleo_formal": 345000, "pea": 620},
    "02": {"itaee": 2.1, "desocupacion": 2.1, "empleo_formal": 870000, "pea": 1850},
    "03": {"itaee": 1.5, "desocupacion": 2.8, "empleo_formal": 155000, "pea": 380},
    "04": {"itaee": 1.2, "desocupacion": 3.0, "empleo_formal": 120000, "pea": 430},
    "05": {"itaee": 1.9, "desocupacion": 2.3, "empleo_formal": 610000, "pea": 1380},
    "06": {"itaee": 1.4, "desocupacion": 2.6, "empleo_formal": 145000, "pea": 360},
    "07": {"itaee": 0.8, "desocupacion": 3.5, "empleo_formal": 310000, "pea": 2100},
    "08": {"itaee": 2.0, "desocupacion": 2.0, "empleo_formal": 520000, "pea": 1780},
    "09": {"itaee": 1.6, "desocupacion": 3.1, "empleo_formal": 3250000, "pea": 5200},
    "10": {"itaee": 1.3, "desocupacion": 2.9, "empleo_formal": 195000, "pea": 820},
    "11": {"itaee": 2.2, "desocupacion": 2.7, "empleo_formal": 810000, "pea": 2900},
    "12": {"itaee": 0.7, "desocupacion": 3.8, "empleo_formal": 220000, "pea": 1700},
    "13": {"itaee": 1.4, "desocupacion": 3.2, "empleo_formal": 280000, "pea": 1400},
    "14": {"itaee": 1.9, "desocupacion": 2.8, "empleo_formal": 1850000, "pea": 4100},
    "15": {"itaee": 1.5, "desocupacion": 3.6, "empleo_formal": 2100000, "pea": 8200},
    "16": {"itaee": 1.1, "desocupacion": 3.3, "empleo_formal": 510000, "pea": 2100},
    "17": {"itaee": 1.7, "desocupacion": 3.0, "empleo_formal": 310000, "pea": 980},
    "18": {"itaee": 1.2, "desocupacion": 3.1, "empleo_formal": 135000, "pea": 600},
    "19": {"itaee": 2.5, "desocupacion": 2.2, "empleo_formal": 1580000, "pea": 2900},
    "20": {"itaee": 0.9, "desocupacion": 3.4, "empleo_formal": 265000, "pea": 1900},
    "21": {"itaee": 1.6, "desocupacion": 3.5, "empleo_formal": 780000, "pea": 2900},
    "22": {"itaee": 2.3, "desocupacion": 2.4, "empleo_formal": 580000, "pea": 1100},
    "23": {"itaee": 2.1, "desocupacion": 2.2, "empleo_formal": 290000, "pea": 650},
    "24": {"itaee": 1.4, "desocupacion": 2.9, "empleo_formal": 330000, "pea": 1350},
    "25": {"itaee": 1.8, "desocupacion": 2.5, "empleo_formal": 490000, "pea": 1450},
    "26": {"itaee": 2.0, "desocupacion": 2.0, "empleo_formal": 560000, "pea": 1400},
    "27": {"itaee": 1.0, "desocupacion": 3.6, "empleo_formal": 195000, "pea": 1050},
    "28": {"itaee": 1.7, "desocupacion": 2.6, "empleo_formal": 610000, "pea": 1800},
    "29": {"itaee": 1.5, "desocupacion": 3.4, "empleo_formal": 195000, "pea": 630},
    "30": {"itaee": 0.9, "desocupacion": 3.7, "empleo_formal": 620000, "pea": 3800},
    "31": {"itaee": 2.0, "desocupacion": 2.3, "empleo_formal": 410000, "pea": 1050},
    "32": {"itaee": 1.1, "desocupacion": 2.8, "empleo_formal": 155000, "pea": 680},
}


def _get(url: str, timeout: int = 20) -> Any:
    req = ur.Request(url, headers={"User-Agent": "predik-geo/1.0", "Accept": "application/json"})
    raw = ur.urlopen(req, timeout=timeout).read()
    return json.loads(raw.decode("utf-8"))


def _periodo_a_fecha(periodo: str) -> Optional[date]:
    try:
        parts = periodo.replace("-", "/").split("/")
        return date(int(parts[0]), int(parts[1]), 1)
    except Exception:
        return None


def fetch_serie(
    indicador_key: str,
    estado_clave: str,
    token: str,
    recientes: bool = False,
) -> List[Dict[str, Any]]:
    """
    Descarga la serie completa de un indicador (nivel nacional).
    estado_clave se almacena en el registro pero la consulta es nacional
    porque los IDs de indicadores estatales son distintos por entidad.
    """
    meta = INDICADORES.get(indicador_key)
    if not meta:
        raise ValueError(f"Indicador desconocido: {indicador_key}")

    ind_id = meta["id"]
    recientes_str = "true" if recientes else "false"
    url = f"{_BASE_URL}/INDICATOR/{ind_id}/es/{_AREA_NACIONAL}/{recientes_str}/BIE-BISE/2.0/{token}?type=json"

    data = _get(url)

    if isinstance(data, list):
        # Error devuelto como lista ["ErrorInfo:...", ...]
        return []
    series = data.get("Series", []) if isinstance(data, dict) else []
    if not series:
        return []

    serie = series[0]
    results = []
    for obs in serie.get("OBSERVATIONS", []):
        periodo = obs.get("TIME_PERIOD", "")
        raw_val = obs.get("OBS_VALUE", "")
        try:
            valor = float(raw_val)
        except (ValueError, TypeError):
            continue
        results.append({
            "indicador_id": ind_id,
            "nombre": meta["nombre"],
            "descripcion": meta["descripcion"],
            "unidad": meta["unidad"],
            "frecuencia": meta["freq_label"],
            "area_clave": _AREA_NACIONAL,
            "estado_clave": estado_clave.zfill(2),
            "periodo": periodo,
            "periodo_fecha": _periodo_a_fecha(periodo),
            "valor": valor,
            "fuente": "BIE_INEGI",
            "loaded_at": datetime.now(timezone.utc),
        })
    return results


def demo_resumen_estado(estado_clave: str) -> Dict[str, Any]:
    clave = estado_clave.zfill(2)
    vals = _DEMO.get(clave, {
        "itaee": 1.5, "desocupacion": 3.2, "empleo_formal": 400000, "pea": 1000,
    })
    return {
        "fuente": "demo",
        "periodo_referencia": "2024/T1",
        "advertencia": "Datos demostrativos. Configure INEGI_BIE_API_TOKEN para datos reales.",
        "indicadores": {
            "itaee": {
                "valor": vals["itaee"],
                "nombre": INDICADORES["itaee"]["nombre"],
                "unidad": INDICADORES["itaee"]["unidad"],
                "interpretacion": _interpretar_itaee(vals["itaee"]),
            },
            "desocupacion": {
                "valor": vals["desocupacion"],
                "nombre": INDICADORES["desocupacion"]["nombre"],
                "unidad": INDICADORES["desocupacion"]["unidad"],
                "interpretacion": _interpretar_desocupacion(vals["desocupacion"]),
            },
            "empleo_formal": {
                "valor": vals["empleo_formal"],
                "nombre": INDICADORES["empleo_formal"]["nombre"],
                "unidad": INDICADORES["empleo_formal"]["unidad"],
                "interpretacion": "Trabajadores con seguridad social IMSS",
            },
            "pea": {
                "valor": vals["pea"],
                "nombre": "Población Económicamente Activa",
                "unidad": "Miles de personas",
                "interpretacion": "Miles de personas económicamente activas",
            },
        },
    }


def _interpretar_itaee(valor: float) -> str:
    if valor >= 3.0:
        return "Actividad económica en expansión fuerte"
    if valor >= 1.5:
        return "Crecimiento económico moderado"
    if valor >= 0.0:
        return "Crecimiento lento, economía estable"
    return "Contracción económica"


def _interpretar_desocupacion(valor: float) -> str:
    if valor <= 2.0:
        return "Desempleo muy bajo — mercado laboral robusto"
    if valor <= 3.0:
        return "Desempleo bajo — buena absorción laboral"
    if valor <= 4.5:
        return "Desempleo moderado — promedio nacional"
    return "Desempleo alto — mercado laboral presionado"


class BIEConnector(BaseConnector):
    name = "inegi_bie"
    requires_auth = True

    async def fetch(self, polygon: Optional[Dict[str, Any]] = None, **params) -> List[GeoFeature]:
        return []

    def health_check(self) -> bool:
        token = os.getenv("INEGI_BIE_API_TOKEN", "")
        if not token:
            return False
        try:
            ind = list(INDICADORES.values())[0]
            url = f"{_BASE_URL}/INDICATOR/{ind['id']}/es/{_AREA_NACIONAL}/true/BIE-BISE/2.0/{token}?type=json"
            data = _get(url, timeout=10)
            return isinstance(data, dict) and "Series" in data
        except Exception:
            return False
