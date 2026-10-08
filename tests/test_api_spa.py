"""Integração da API com SQLite real, sem tocar no banco configurado do usuário."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import main as api
from config.database import Base
from models.database_models import Produto, Usuario
from services.auth_service import AuthService

@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(api, "SessionLocal", factory)
    monkeypatch.setattr(api, "init_db", lambda: None)
    with factory() as db:
        db.add(Usuario(nome_usuario="admin", senha_hash=AuthService.hash_password("senha-segura-de-teste"),
                       nivel_acesso="admin", ativo=True))
        db.add(Usuario(nome_usuario="caixa", senha_hash=AuthService.hash_password("senha-caixa-segura"),
                       nivel_acesso="funcionario", ativo=True))
        db.commit()
    with TestClient(api.app) as instance:
        yield instance, factory
    engine.dispose()

def login(client, username="admin", password="senha-segura-de-teste"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf"]}

def product_payload(**changes):
    return {
        "nome":"Expresso", "categoria":"café","preco_venda":8,
        "custo_unitario":3,"estoque_atual":10,"estoque_minimo":3,"unidade":"un",
        **changes
    }

def test_public_health_and_private_data(client):
    http, _ = client
    assert http.get("/api/health").json() == {"status": "ok"}
    assert http.get("/api/products").status_code == 401
    assert http.post("/api/auth/login", json={"username": "admin", "password": "errada"}).status_code == 401

def test_auth_csrf_and_permissions(client):
    http, _ = client
    csrf = login(http, "caixa", "senha-caixa-segura")
    assert http.get("/api/auth/me").status_code == 200
    assert http.post("/api/products", json=product_payload()).status_code == 403
    assert http.post("/api/products", json=product_payload(), headers=csrf).status_code == 403
    assert http.get("/api/employees").status_code == 403
    assert http.post("/api/auth/logout", headers=csrf).status_code == 200
    assert http.get("/api/products").status_code == 401

def test_product_sale_stock_and_insufficient_inventory(client):
    http, factory = client
    csrf = login(http)
    assert http.post("/api/products", json=product_payload()).status_code == 403
    response = http.post("/api/products", json=product_payload(), headers=csrf)
    assert response.status_code == 201, response.text
    pid = response.json()["id"]
    payload = {"metodo_pagamento": "pix", "itens": [{"id_produto": pid, "quantidade": 2}]}
    sale = http.post("/api/sales", json=payload, headers=csrf)
    assert sale.status_code == 201, sale.text
    assert sale.json()["valor_total"] == 16.0
    assert http.get("/api/products").json()[0]["estoque_atual"] == 8
    denied = http.post("/api/sales", json={"metodo_pagamento":"pix",
        "itens":[{"id_produto":pid,"quantidade":50}]}, headers=csrf)
    assert denied.status_code == 409
    assert http.get("/api/products").json()[0]["estoque_atual"] == 8
    assert len(http.get("/api/sales").json()) == 1

def test_purchase_cost_average_and_dashboard(client):
    http, _ = client
    csrf=login(http)
    p=http.post("/api/products", json=product_payload(), headers=csrf).json()
    buy=http.post("/api/purchases", json={
        "fornecedor":"Distribuidora", "metodo_pagamento":"pix",
        "itens":[{"id_produto":p["id"],"quantidade":10,"preco_unitario":5}]
    },headers=csrf)
    assert buy.status_code==201,buy.text
    assert buy.json()["valor_total"]==50.0
    stock=http.get("/api/products").json()[0]
    assert stock["estoque_atual"]==20
    assert stock["custo_unitario"]==4.0
    dashboard=http.get("/api/dashboard?days=30")
    assert dashboard.status_code==200
    assert dashboard.json()["compras"]==50.0
    assert http.get("/api/bi?days=30").status_code==200

def test_validations(client):
    http, _ = client
    csrf=login(http)
    invalid=http.post("/api/products",json=product_payload(preco_venda=-2),headers=csrf)
    assert invalid.status_code==422
    assert http.post("/api/sales",json={"metodo_pagamento":"pix","itens":[]},headers=csrf).status_code==422
