"""
Seed de datos mínimos para ambiente de desarrollo.
Crea una organización y un usuario admin si no existen.
Idempotente: seguro de correr múltiples veces.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bcrypt
from sqlalchemy import select

from app.db import SessionLocal
from app.models.core import Organization, User

ORG_NAME = "Demo Org"
ADMIN_EMAIL = "admin@predik.local"
ADMIN_PASSWORD = "dev_password_admin"


def seed():
    db = SessionLocal()
    try:
        # Organización
        org = db.execute(
            select(Organization).where(Organization.name == ORG_NAME)
        ).scalar_one_or_none()

        if not org:
            org = Organization(name=ORG_NAME, plan="starter")
            db.add(org)
            db.flush()
            print(f"[seed] Organización creada: {ORG_NAME} (id={org.id})")
        else:
            print(f"[seed] Organización ya existe: {ORG_NAME} (id={org.id})")

        # Usuario admin
        user = db.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        ).scalar_one_or_none()

        if not user:
            user = User(
                organization_id=org.id,
                email=ADMIN_EMAIL,
                hashed_password=bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode(),
                role="admin",
            )
            db.add(user)
            print(f"[seed] Usuario creado: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        else:
            print(f"[seed] Usuario ya existe: {ADMIN_EMAIL}")

        db.commit()
        print("[seed] Listo.")

    except Exception as e:
        db.rollback()
        print(f"[seed] ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
