"""
Servicio BIE — consulta indicadores macroeconómicos por estado.

Flujo:
  1. Si hay token → consulta BD (cache) o API BIE en vivo
  2. Si no hay token → devuelve datos demo con valores históricos reales

Uso típico: enriquecer el análisis de zona con contexto económico estatal.
"""
import logging
import os
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.connectors.inegi.bie import (
    INDICADORES,
    demo_resumen_estado,
    fetch_serie,
    _ESTADO_A_AREA,
    _interpretar_itaee,
    _interpretar_desocupacion,
)
from app.models.raw_data import BieIndicador

logger = logging.getLogger(__name__)

_FECHA_INICIO_DEFAULT = "2020/01"
_FECHA_FIN_DEFAULT = "2024/12"


# ── Carga / ETL ────────────────────────────────────────────────────────────────

def cargar_indicadores_estado(
    db: Session,
    estado_clave: str,
    token: str,
    fecha_inicio: str = _FECHA_INICIO_DEFAULT,
    fecha_fin: str = _FECHA_FIN_DEFAULT,
) -> Dict[str, int]:
    """
    Descarga todos los indicadores BIE para un estado y los upserta en BD.
    Retorna dict {indicador_key: n_registros_cargados}.
    """
    resultados: Dict[str, int] = {}
    for key in INDICADORES:
        try:
            registros = fetch_serie(key, estado_clave, token, fecha_inicio, fecha_fin)
            if registros:
                _upsert_registros(db, registros)
                db.commit()
            resultados[key] = len(registros)
            logger.info(
                "BIE cargado: estado=%s indicador=%s registros=%d",
                estado_clave, key, len(registros),
            )
        except Exception:
            logger.exception("Error cargando BIE estado=%s indicador=%s", estado_clave, key)
            resultados[key] = 0
    return resultados


def _upsert_registros(db: Session, registros: List[Dict[str, Any]]) -> None:
    stmt = pg_insert(BieIndicador).values(registros)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_bie_ind_area_periodo",
        set_={
            "valor":      stmt.excluded.valor,
            "nombre":     stmt.excluded.nombre,
            "unidad":     stmt.excluded.unidad,
            "loaded_at":  stmt.excluded.loaded_at,
        },
    )
    db.execute(stmt)


# ── Consulta / Lectura ─────────────────────────────────────────────────────────

def resumen_economico_estado(db: Session, estado_clave: str) -> Dict[str, Any]:
    """
    Devuelve el resumen económico de un estado para mostrar en el sidebar.
    Usa BD si hay datos; si no, datos demo.
    """
    clave = estado_clave.zfill(2)
    area = _ESTADO_A_AREA.get(clave)

    if not area:
        return demo_resumen_estado(clave)

    # Buscar el último valor de cada indicador en BD
    indicadores_resp: Dict[str, Any] = {}
    tiene_datos = False

    for key, meta in INDICADORES.items():
        row = db.execute(
            text("""
                SELECT valor, periodo, periodo_fecha, unidad, nombre
                FROM raw_data.bie_indicadores
                WHERE indicador_id = :ind_id AND estado_clave = :est
                ORDER BY periodo_fecha DESC NULLS LAST
                LIMIT 1
            """),
            {"ind_id": meta["id"], "est": clave},
        ).fetchone()

        if row and row.valor is not None:
            tiene_datos = True
            indicadores_resp[key] = {
                "valor":      row.valor,
                "nombre":     row.nombre or meta["nombre"],
                "unidad":     row.unidad or meta["unidad"],
                "periodo":    row.periodo,
                "interpretacion": _interpretar_indicador(key, row.valor),
            }

    if not tiene_datos:
        return demo_resumen_estado(clave)

    return {
        "fuente": "BIE_INEGI",
        "estado_clave": clave,
        "advertencia": None,
        "indicadores": indicadores_resp,
    }


def serie_historica(
    db: Session,
    estado_clave: str,
    indicador_key: str,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    """Retorna la serie histórica de un indicador para un estado (últimos N periodos)."""
    clave = estado_clave.zfill(2)
    meta = INDICADORES.get(indicador_key)
    if not meta:
        return []

    rows = db.execute(
        text("""
            SELECT periodo, periodo_fecha, valor
            FROM raw_data.bie_indicadores
            WHERE indicador_id = :ind_id AND estado_clave = :est
              AND valor IS NOT NULL
            ORDER BY periodo_fecha DESC NULLS LAST
            LIMIT :lim
        """),
        {"ind_id": meta["id"], "est": clave, "lim": limit},
    ).fetchall()

    return [
        {"periodo": r.periodo, "fecha": r.periodo_fecha.isoformat() if r.periodo_fecha else None, "valor": r.valor}
        for r in reversed(rows)
    ]


def stats_carga(db: Session) -> Dict[str, Any]:
    """Estadísticas de cobertura de datos BIE en BD."""
    total = db.execute(
        text("SELECT COUNT(*) FROM raw_data.bie_indicadores")
    ).scalar() or 0

    estados = db.execute(
        text("SELECT COUNT(DISTINCT estado_clave) FROM raw_data.bie_indicadores")
    ).scalar() or 0

    ultima_carga = db.execute(
        text("SELECT MAX(loaded_at) FROM raw_data.bie_indicadores")
    ).scalar()

    token_ok = bool(os.getenv("INEGI_BIE_API_TOKEN", ""))

    return {
        "total_registros": total,
        "estados_con_datos": estados,
        "ultima_carga": ultima_carga.isoformat() if ultima_carga else None,
        "token_configurado": token_ok,
        "indicadores_disponibles": list(INDICADORES.keys()),
    }


def _interpretar_indicador(key: str, valor: float) -> str:
    if key == "itaee":
        return _interpretar_itaee(valor)
    if key == "desocupacion":
        return _interpretar_desocupacion(valor)
    if key == "empleo_formal":
        if valor >= 1_000_000:
            return f"{valor/1_000_000:.1f}M trabajadores formales — mercado laboral amplio"
        return f"{valor:,.0f} trabajadores formales"
    if key == "pea":
        return f"{valor:,.0f} miles de personas económicamente activas"
    return ""
