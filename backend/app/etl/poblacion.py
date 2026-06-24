"""ETL de población — reemplazado por consultas directas a ageb_demographics + ageb_geometries."""
from sqlalchemy.orm import Session


def run_poblacion_etl(db: Session, **kwargs) -> int:
    """No-op: el cubo H3 de población fue eliminado. Los datos se consultan directamente desde AGEBs."""
    return 0
