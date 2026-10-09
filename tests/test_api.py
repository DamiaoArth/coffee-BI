from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from config.clock import business_today
from config.database import SessionLocal
from models.database_models import ItemVenda, Produto, Venda
from services.auth_service import AuthService
from services.relatorio_service import RelatorioService
from services.venda_service import VendaService


def movement(product, qty=2, price="8.50"):
    return {
        "data": str(business_today()),
        "metodo_pagamento": "Pix",
        "itens": [
            {"id_produto": product["id"], "quantidade": qty, "preco_unitario": price}
        ],
    }


def test_real_product_crud_and_persistence(admin, product):
    id = product["id"]
    updated = {
        k: product[k]
        for k in [
            "nome",
            "categoria",
            "preco_venda",
            "custo_unitario",
            "estoque_atual",
            "estoque_minimo",
            "unidade",
            "ativo",
        ]
    }
    updated.update(nome="Matcha", preco_venda="25.00")
    assert (
        admin.put(
            f"/api/products/{id}",
            json=updated,
            headers={"If-Match": str(product["version"])},
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        row = db.get(Produto, id)
        assert row.nome == "Matcha" and row.preco_venda == Decimal("25.00")
    assert admin.get("/api/products?q=Matcha").json()["total"] == 1
    assert admin.delete(f"/api/products/{id}").status_code == 204
    assert admin.get("/api/products?active=true").json()["total"] == 0
    assert admin.get(f"/api/products/{id}").json()["ativo"] is False
    updated["ativo"] = True
    assert (
        admin.put(
            f"/api/products/{id}",
            json=updated,
            headers={
                "If-Match": str(admin.get(f"/api/products/{id}").json()["version"])
            },
        ).status_code
        == 200
    )
    assert admin.get("/api/products?active=true").json()["total"] == 1


def test_validation_and_missing_rows(admin):
    base = {"nome": "Valid", "categoria": "café", "preco_venda": "2.50"}
    for changes in [
        {"nome": "  "},
        {"estoque_atual": -1},
        {"estoque_minimo": -1},
        {"preco_venda": "NaN"},
        {"preco_venda": "0.001"},
        {"estoque_atual": 1.5},
        {"id": 99},
    ]:
        assert admin.post("/api/products", json={**base, **changes}).status_code == 422
    assert admin.get("/api/products/99999").status_code == 404
    assert admin.delete("/api/products/99999").status_code == 404
    assert admin.get("/api/products?sort=unknown").status_code == 422
    assert admin.get("/api/products?page=0").status_code == 422
    assert admin.get("/api/products?page_size=101").status_code == 422


def test_permissions_and_logout(client):
    assert client.get("/api/products").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json={"username": "caixa", "password": "test-password"}
        ).status_code
        == 200
    )
    assert client.get("/api/products").status_code == 200
    assert (
        client.post(
            "/api/products", json={"nome": "X", "categoria": "X", "preco_venda": 1}
        ).status_code
        == 403
    )
    for path in ["employees", "transactions", "purchases"]:
        assert client.get("/api/" + path).status_code == 403
    cookie = client.cookies.get("coffee_session")
    assert client.post("/api/auth/logout").status_code == 204
    assert (
        client.get(
            "/api/auth/me", headers={"Cookie": f"coffee_session={cookie}"}
        ).status_code
        == 401
    )


def test_origin_protection(admin):
    assert (
        admin.post(
            "/api/auth/logout", headers={"Origin": "https://attacker.invalid"}
        ).status_code
        == 403
    )
    assert admin.get("/api/auth/me").status_code == 200


def test_sale_atomic_total_and_cancellation(admin, product):
    payload = movement(product)
    response = admin.post("/api/sales", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert Decimal(data["valor_total"]) == Decimal("17.00")
    assert admin.get(f"/api/products/{product['id']}").json()["estoque_atual"] == 8
    assert (
        admin.get(f"/api/sales/{data['id']}").json()["itens"][0]["produto_nome"]
        == "Café"
    )
    assert admin.delete(f"/api/sales/{data['id']}").status_code == 204
    assert admin.delete(f"/api/sales/{data['id']}").status_code == 404
    assert admin.get(f"/api/products/{product['id']}").json()["estoque_atual"] == 10
    with SessionLocal() as db:
        assert db.query(ItemVenda).count() == 0


def test_insufficient_stock_rolls_back_every_item(admin, product):
    second = admin.post(
        "/api/products",
        json={
            "nome": "Sem estoque",
            "categoria": "café",
            "preco_venda": "5",
            "estoque_atual": 0,
        },
    ).json()
    payload = movement(product)
    payload["itens"].append({"id_produto": second["id"], "quantidade": 1})
    assert admin.post("/api/sales", json=payload).status_code == 409
    assert admin.get(f"/api/products/{product['id']}").json()["estoque_atual"] == 10
    assert admin.get("/api/sales").json()["total"] == 0
    # Duplicate product lines must respect cumulative quantity.
    payload = movement(product, 6)
    payload["itens"] *= 2
    assert admin.post("/api/sales", json=payload).status_code == 409
    assert admin.get(f"/api/products/{product['id']}").json()["estoque_atual"] == 10


def test_purchase_weighted_cost_and_cancel_guards(admin, product):
    payload = movement(product, 10, "4.00")
    payload["fornecedor"] = "Fornecedor A"
    response = admin.post("/api/purchases", json=payload)
    assert response.status_code == 201, response.text
    p = admin.get(f"/api/products/{product['id']}").json()
    assert p["estoque_atual"] == 20
    assert Decimal(p["custo_unitario"]) == Decimal("3.00")
    assert admin.post("/api/sales", json=movement(product, 15)).status_code == 201
    id = response.json()["id"]
    assert admin.delete(f"/api/purchases/{id}").status_code == 409
    assert admin.get(f"/api/purchases/{id}").status_code == 200
    assert admin.get(f"/api/products/{product['id']}").json()["estoque_atual"] == 5


def test_invalid_purchase_rolls_back(admin, product):
    payload = movement(product, 10, "4.00")
    payload["fornecedor"] = "A"
    payload["itens"].append(
        {"id_produto": 99999, "quantidade": 1, "preco_unitario": "2"}
    )
    assert admin.post("/api/purchases", json=payload).status_code == 409
    p = admin.get(f"/api/products/{product['id']}").json()
    assert p["estoque_atual"] == 10 and Decimal(p["custo_unitario"]) == Decimal("2")
    assert admin.get("/api/purchases").json()["total"] == 0


def test_employee_and_transaction_crud(admin):
    employee = {"nome": "Ana", "cargo": "barista", "email": "ana@example.com"}
    r = admin.post("/api/employees", json=employee)
    assert r.status_code == 201, r.text
    id = r.json()["id"]
    with SessionLocal() as db:
        AuthService.criar_usuario(db, "ana", "test-password", "caixa", id)
    assert (
        admin.put(
            f"/api/employees/{id}", json={**employee, "cargo": "gerente"}
        ).status_code
        == 200
    )
    assert admin.delete(f"/api/employees/{id}").status_code == 204
    assert (
        admin.post(
            "/api/auth/login", json={"username": "ana", "password": "test-password"}
        ).status_code
        == 401
    )
    tx = {
        "tipo": "saída",
        "descricao": "Aluguel",
        "valor": "1200",
        "categoria": "fixo",
        "data": str(business_today()),
    }
    r = admin.post("/api/transactions", json=tx)
    assert r.status_code == 201, r.text
    id = r.json()["id"]
    assert (
        admin.put(f"/api/transactions/{id}", json={**tx, "valor": "1250"}).status_code
        == 200
    )
    assert Decimal(admin.get(f"/api/transactions/{id}").json()["valor"]) == Decimal(
        "1250"
    )
    assert admin.delete(f"/api/transactions/{id}").status_code == 204
    assert admin.get(f"/api/transactions/{id}").status_code == 404


def test_dashboard_reports_and_snapshot_cost(admin, product):
    with SessionLocal() as db:
        assert RelatorioService.fluxo_caixa(
            db, business_today(), business_today()
        ).empty
    assert admin.post("/api/sales", json=movement(product)).status_code == 201
    payload = movement(product, 2, "4.00")
    payload["fornecedor"] = "A"
    assert admin.post("/api/purchases", json=payload).status_code == 201
    assert (
        admin.post(
            "/api/transactions",
            json={
                "tipo": "saída",
                "descricao": "Extra",
                "valor": "1.00",
                "categoria": "outro",
            },
        ).status_code
        == 201
    )
    d = admin.get("/api/dashboard").json()
    assert d["revenue"] == 17 and d["sales_count"] == 1 and d["cash_balance"] == 8
    assert (
        admin.get("/api/dashboard?start=2026-10-02&end=2026-10-01").status_code == 422
    )
    with SessionLocal() as db:
        report = RelatorioService.fluxo_caixa(db, business_today(), business_today())
        assert float(report["saldo"].sum()) == 8
        profits = RelatorioService.lucro_por_produto(
            db, business_today(), business_today()
        )
        assert float(profits["Custo"].sum()) == 4  # original cost, not new average


def test_pagination_sort_and_unicode(admin):
    for name in ["Éclair", "Café", "Matcha"]:
        assert (
            admin.post(
                "/api/products",
                json={"nome": name, "categoria": "chá", "preco_venda": "5"},
            ).status_code
            == 201
        )
    first = admin.get("/api/products?page_size=2&sort=id&direction=asc").json()
    second = admin.get("/api/products?page_size=2&page=2&sort=id&direction=asc").json()
    assert (
        first["total"] == 3 and len(first["items"]) == 2 and len(second["items"]) == 1
    )
    assert first["items"][0]["nome"] == "Éclair"
    assert admin.get("/api/products?q=Caf%C3%A9").json()["items"][0]["nome"] == "Café"


def test_service_recalculates_untrusted_subtotals(admin, product):
    with SessionLocal() as db:
        sale = VendaService.criar_venda(
            db,
            business_today(),
            "Pix",
            [
                {
                    "id_produto": product["id"],
                    "quantidade": 2,
                    "preco_unitario": Decimal("8.50"),
                    "subtotal": Decimal("0.01"),
                }
            ],
        )
        assert sale.valor_total == Decimal("17.00")


def test_concurrent_sales_cannot_oversell(admin, product):
    def sell():
        with SessionLocal() as db:
            try:
                VendaService.criar_venda(
                    db, business_today(), "Pix", movement(product, 7)["itens"]
                )
                return True
            except ValueError:
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: sell(), range(2)))
    assert sorted(results) == [False, True]
    with SessionLocal() as db:
        assert db.get(Produto, product["id"]).estoque_atual == 3
        assert db.query(Venda).count() == 1


def test_stale_product_editor_cannot_overwrite_sale_stock(admin, product):
    payload = {
        k: product[k]
        for k in [
            "nome",
            "categoria",
            "preco_venda",
            "custo_unitario",
            "estoque_atual",
            "estoque_minimo",
            "unidade",
            "ativo",
        ]
    }
    assert admin.post("/api/sales", json=movement(product)).status_code == 201
    response = admin.put(
        f"/api/products/{product['id']}",
        json=payload,
        headers={"If-Match": str(product["version"])},
    )
    assert response.status_code == 409
    assert admin.get(f"/api/products/{product['id']}").json()["estoque_atual"] == 8


def test_concurrent_cancellation_restores_stock_once(admin, product):
    from services.venda_service import VendaService

    sale = admin.post("/api/sales", json=movement(product)).json()

    def cancel():
        with SessionLocal() as db:
            return VendaService.cancelar_venda(db, sale["id"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: cancel(), range(2)))
    assert sorted(results) == [False, True]
    with SessionLocal() as db:
        assert db.get(Produto, product["id"]).estoque_atual == 10


def test_zero_revenue_profit_report_does_not_divide_by_zero(admin, product):
    assert (
        admin.post("/api/sales", json=movement(product, 1, "0.00")).status_code == 201
    )
    with SessionLocal() as db:
        result = RelatorioService.lucro_por_produto(
            db, business_today(), business_today()
        )
        assert result["Margem %"].iloc[0] == 0
        assert result["Lucro"].iloc[0] == -2


def test_password_reset_revokes_existing_api_session(admin):
    from models.database_models import Usuario

    cookie = admin.cookies.get("coffee_session")
    with SessionLocal() as db:
        user = db.query(Usuario).filter_by(nome_usuario="admin").one()
        AuthService.redefinir_senha(db, user.id, "changed-password")
    assert (
        admin.get(
            "/api/auth/me", headers={"Cookie": f"coffee_session={cookie}"}
        ).status_code
        == 401
    )
    assert (
        admin.post(
            "/api/auth/login", json={"username": "admin", "password": "test-password"}
        ).status_code
        == 401
    )
    assert (
        admin.post(
            "/api/auth/login",
            json={"username": "admin", "password": "changed-password"},
        ).status_code
        == 200
    )
