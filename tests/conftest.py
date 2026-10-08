import os
import tempfile
from pathlib import Path

# Set before application imports. Never touch the user's database.
_test_dir = tempfile.TemporaryDirectory(prefix="coffee-bi-tests-")
os.environ["DATABASE_URL"] = os.getenv(
    "COFFEE_TEST_DATABASE_URL", "sqlite:///" + str(Path(_test_dir.name) / "test.db")
)
os.environ.pop("ADMIN_PASSWORD", None)

import pytest
from fastapi.testclient import TestClient

from api.main import app
from config.database import Base, SessionLocal, engine
from services.auth_service import AuthService


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        AuthService.criar_usuario(db, "admin", "test-password", "admin")
        AuthService.criar_usuario(db, "caixa", "test-password", "caixa")
    with TestClient(app) as client:
        yield client


@pytest.fixture
def admin(client):
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "test-password"}
        ).status_code
        == 200
    )
    return client


@pytest.fixture
def product(admin):
    response = admin.post(
        "/api/products",
        json={
            "nome": "Café",
            "categoria": "café",
            "preco_venda": "8.50",
            "custo_unitario": "2.00",
            "estoque_atual": 10,
            "estoque_minimo": 2,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
