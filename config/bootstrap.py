"""Idempotent user bootstrap, shared by all entry points."""

import os

from config.database import SessionLocal
from models.database_models import Usuario
from services.auth_service import AuthService


def bootstrap_users():
    with SessionLocal() as db:
        for username, password, role in [
            (
                os.getenv("ADMIN_USERNAME", "admin"),
                os.getenv("ADMIN_PASSWORD"),
                "admin",
            ),
            (
                os.getenv("CAIXA_USERNAME", "caixa"),
                os.getenv("CAIXA_PASSWORD"),
                "caixa",
            ),
        ]:
            if (
                password
                and not db.query(Usuario).filter_by(nome_usuario=username).first()
            ):
                AuthService.criar_usuario(db, username, password, role)
