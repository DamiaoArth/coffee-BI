"""Real Cloud Firestore integration tests using Firebase Local Emulator Suite.

Never run these destructive fixture resets against a live Firebase project.
"""
import os

import pytest
from fastapi.testclient import TestClient

from api import main as api
from api.firebase_db import get_firestore
from api.passwords import PasswordService


@pytest.fixture
def client():
    if not os.getenv("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Configure FIRESTORE_EMULATOR_HOST to run Firestore integration tests.")
    project = os.getenv("FIREBASE_PROJECT_ID")
    if project != "demo-coffee-bi":
        pytest.skip("Tests require the isolated demo-coffee-bi emulator project.")

    db = get_firestore()
    for name in ("users", "usernames", "employees", "products", "sales", "purchases",
                 "transactions", "_counters"):
        for snapshot in db.collection(name).stream():
            snapshot.reference.delete()

    api.register_user(
        db, username="admin", password_hash=PasswordService.hash_password(
            "senha-segura-de-teste"
        ), role="admin",
    )
    api.register_user(
        db, username="caixa", password_hash=PasswordService.hash_password(
            "senha-caixa-segura"
        ), role="funcionario",
    )
    with TestClient(api.app) as http:
        yield http, db


def login(http, username="admin", password="senha-segura-de-teste"):
    response = http.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf"]}


def product_payload(**changes):
    return {
        "nome": "Expresso", "categoria": "café", "preco_venda": 8,
        "custo_unitario": 3, "estoque_atual": 10,
        "estoque_minimo": 3, "unidade": "un", **changes,
    }


def test_healthy_api_and_private_data(client):
    http, db = client
    assert http.get("/api/health").json() == {"status": "ok", "database": "firestore"}
    assert http.get("/api/products").status_code == 401
    assert http.post("/api/auth/login", json={
        "username": "admin", "password": "invalida"
    }).status_code == 401


def test_login_csrf_rbac_logout(client):
    http, db = client
    csrf = login(http, "caixa", "senha-caixa-segura")
    assert http.get("/api/auth/me").status_code == 200
    assert http.post("/api/products", json=product_payload()).status_code == 403
    assert http.post("/api/products", headers=csrf, json=product_payload()).status_code == 403
    assert http.get("/api/employees").status_code == 403
    assert http.post("/api/auth/logout", headers=csrf).status_code == 200
    assert http.get("/api/products").status_code == 401



def test_product_crud_persists_and_is_visible(client):
    http, db = client
    csrf = login(http)

    created = http.post(
        "/api/products", headers=csrf,
        json=product_payload(nome="Cold Brew", preco_venda=18.5, estoque_atual=12),
    )
    assert created.status_code == 201, created.text
    product = created.json()
    pid = product["id"]

    snap = db.collection("products").document(str(pid)).get()
    assert snap.exists
    assert snap.to_dict()["nome"] == "Cold Brew"
    listed = http.get("/api/products")
    assert listed.status_code == 200
    assert any(x["id"] == pid and x["nome"] == "Cold Brew" for x in listed.json())

    updated = http.put(
        f"/api/products/{pid}", headers=csrf,
        json=product_payload(nome="Cold Brew 500ml", preco_venda=21, estoque_atual=9),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["nome"] == "Cold Brew 500ml"
    listed_after_update = http.get("/api/products").json()
    assert any(x["id"] == pid and x["nome"] == "Cold Brew 500ml" for x in listed_after_update)

    archived = http.delete(f"/api/products/{pid}", headers=csrf)
    assert archived.status_code == 200, archived.text
    assert not any(x["id"] == pid for x in http.get("/api/products").json())
    assert any(x["id"] == pid and x["ativo"] is False for x in http.get("/api/products?all=true").json())

def test_atomic_sale_updates_stock_without_overselling(client):
    http, db = client
    csrf = login(http)
    assert http.post("/api/products", json=product_payload()).status_code == 403
    p = http.post("/api/products", json=product_payload(), headers=csrf)
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    # Repeated product IDs must be summed before checking available stock.
    sale = http.post("/api/sales", headers=csrf, json={
        "metodo_pagamento": "pix",
        "itens": [{"id_produto": pid, "quantidade": 1},
                  {"id_produto": pid, "quantidade": 2}],
    })
    assert sale.status_code == 201, sale.text
    assert sale.json()["valor_total"] == 24
    assert http.get("/api/products").json()[0]["estoque_atual"] == 7
    rejected = http.post("/api/sales", headers=csrf, json={
        "metodo_pagamento": "pix", "itens": [
            {"id_produto": pid, "quantidade": 8}
        ],
    })
    assert rejected.status_code == 409
    assert http.get("/api/products").json()[0]["estoque_atual"] == 7
    assert len(http.get("/api/sales").json()) == 1
    dashboard = http.get("/api/dashboard?days=7").json()
    assert len(dashboard["serie"]) == 7
    assert len(dashboard["serie_anterior"]) == 7
    assert {"data", "total", "vendas", "ticket_medio"} <= set(dashboard["serie"][0])
    assert sum(day["vendas"] for day in dashboard["serie"]) == 1


def test_purchase_weighted_average_and_reports(client):
    http, db = client
    csrf = login(http)
    p = http.post("/api/products", json=product_payload(), headers=csrf).json()
    purchase = http.post("/api/purchases", headers=csrf, json={
        "fornecedor": "Distribuidora", "metodo_pagamento": "pix",
        "itens": [
            {"id_produto": p["id"], "quantidade": 6, "preco_unitario": 4.50},
            {"id_produto": p["id"], "quantidade": 4, "preco_unitario": 5.75},
        ],
    })
    assert purchase.status_code == 201, purchase.text
    assert purchase.json()["valor_total"] == 50.0
    product = http.get("/api/products").json()[0]
    assert product["estoque_atual"] == 20
    assert product["custo_unitario"] == 4.00
    assert http.get("/api/dashboard?days=30").json()["compras"] == 50
    assert http.get("/api/bi?days=30").status_code == 200


def test_financial_records_and_employee_management(client):
    http, db = client
    csrf = login(http)
    transaction = http.post("/api/transactions", headers=csrf, json={
        "tipo": "entrada", "descricao": "Dinheiro avulso", "valor": "12.55",
        "categoria": "outros",
    })
    assert transaction.status_code == 201, transaction.text
    assert http.get("/api/transactions").json()[0]["valor"] == 12.55
    assert http.get("/api/bi").json()["entradas"] == 12.55
    assert http.delete("/api/transactions/" + str(transaction.json()["id"]),
                       headers=csrf).status_code == 200
    emp = http.post("/api/employees", headers=csrf, json={
        "nome": "Ana Teste", "cargo": "funcionario", "ativo": True,
    })
    assert emp.status_code == 201, emp.text
    new = http.post("/api/users", headers=csrf, json={
        "nome_usuario": "ana", "senha": "uma-senha-segura",
        "nivel_acesso": "funcionario", "funcionario_id": emp.json()["id"],
    })
    assert new.status_code == 201, new.text
    duplicate = http.post("/api/users", headers=csrf, json={
        "nome_usuario": "ANA", "senha": "outra-senha-segura",
        "nivel_acesso": "funcionario",
    })
    assert duplicate.status_code == 409
    assert len(http.get("/api/employees").json()) == 1


def test_backend_validation(client):
    http, db = client
    csrf = login(http)
    assert http.post("/api/products", headers=csrf, json=product_payload(
        preco_venda=-1,
    )).status_code == 422
    assert http.post("/api/sales", headers=csrf, json={
        "metodo_pagamento": "pix", "itens": [],
    }).status_code == 422
