"""Run isolated real-browser CRUD regression: python tests/browser_smoke.py.

Starts its own server/database; no existing cafeteria data is modified.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "screenshots"
OUTPUT.mkdir(parents=True, exist_ok=True)


def run():
    with tempfile.TemporaryDirectory(prefix="coffee-ui-") as directory:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{directory}/test.db",
            "ADMIN_PASSWORD": "browser-test-password",
            "ADMIN_USERNAME": "admin",
            "COOKIE_SECURE": "false",
        }
        with open(Path(directory) / "server.log", "w") as log:
            server = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "api.main:app", "--port", str(port)],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        if (
                            httpx.get(
                                url + "/api/health", timeout=1, trust_env=False
                            ).status_code
                            == 200
                        ):
                            break
                    except httpx.RequestError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Test server failed to start.")
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    errors, requests, responses = [], [], []
                    page.on("pageerror", lambda error: errors.append(str(error)))

                    def capture_response(response):
                        path = urlsplit(response.url).path
                        if path.startswith("/api/"):
                            responses.append(
                                {
                                    "method": response.request.method,
                                    "path": path,
                                    "status": response.status,
                                }
                            )

                    page.on("response", capture_response)
                    page.on(
                        "request",
                        lambda request: requests.append((request.method, request.url)),
                    )
                    page.goto(url)
                    page.locator("#login-form [name=username]").fill("admin")
                    page.locator("#login-form [name=password]").fill(
                        "browser-test-password"
                    )
                    page.get_by_role("button", name="Entrar no painel").click()
                    expect(page.locator("#page-title")).to_have_text("Visão geral")
                    expect(page.locator(".stats")).to_be_visible()
                    page.locator('nav a[href="#products"]').click()
                    page.get_by_role("button", name="+ Novo produto").click()
                    form = page.locator("#editor-form")
                    form.locator("[name=nome]").fill("Matcha especial")
                    form.locator("[name=preco_venda]").fill("25.00")
                    form.locator("[name=custo_unitario]").fill("7.00")
                    form.locator("[name=estoque_atual]").fill("30")
                    form.locator("[name=estoque_minimo]").fill("5")
                    page.locator("#save-button").click()
                    expect(page.locator("#modal")).not_to_be_visible()
                    expect(page.locator("tbody")).to_contain_text("Matcha especial")
                    page.get_by_role("button", name="Editar", exact=True).click()
                    form.locator("[name=nome]").fill("Matcha premium")
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("Matcha premium")
                    # New page load proves the product survived outside frontend state.
                    page.reload()
                    expect(page.locator("tbody")).to_contain_text("Matcha premium")
                    page.locator('nav a[href="#sales"]').click()
                    page.get_by_role("button", name="+ Registrar venda").click()
                    expect(page.locator(".item-line")).to_have_count(1)
                    form.locator("[name=quantity]").fill("3")
                    page.locator("#save-button").click()
                    expect(page.locator("#modal")).not_to_be_visible()
                    expect(page.locator("tbody")).to_contain_text("75,00")
                    page.get_by_role("button", name="Detalhes", exact=True).click()
                    expect(page.locator("#modal")).to_contain_text("Matcha premium")
                    page.locator("#close-modal").click()
                    page.get_by_role("button", name="+ Registrar venda").click()
                    form.locator("[name=quantity]").fill("99")
                    page.locator("#save-button").click()
                    expect(page.locator("#form-error")).to_contain_text(
                        "Estoque insuficiente"
                    )
                    expect(page.locator("#modal")).to_be_visible()
                    page.locator("#cancel-modal").click()
                    page.get_by_role("button", name="Cancelar", exact=True).click()
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("Nenhum registro")
                    page.locator('nav a[href="#purchases"]').click()
                    page.get_by_role("button", name="+ Registrar compra").click()
                    form.locator("[name=fornecedor]").fill("Fornecedor de teste")
                    form.locator("[name=quantity]").fill("10")
                    form.locator("[name=price]").fill("9.00")
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("90,00")
                    page.get_by_role("button", name="Cancelar", exact=True).click()
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("Nenhum registro")
                    page.locator('nav a[href="#employees"]').click()
                    page.get_by_role("button", name="+ Novo funcionário").click()
                    form.locator("[name=nome]").fill("Ana Silva")
                    form.locator("[name=cargo]").fill("Barista")
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("Ana Silva")
                    page.locator('nav a[href="#transactions"]').click()
                    page.get_by_role("button", name="+ Nova transação").click()
                    form.locator("[name=descricao]").fill("Aluguel de teste")
                    form.locator("[name=valor]").fill("1200")
                    form.locator("[name=categoria]").fill("Custos fixos")
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("Aluguel de teste")
                    page.get_by_role("button", name="Editar", exact=True).click()
                    form.locator("[name=valor]").fill("1250")
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("1.250,00")
                    page.get_by_role("button", name="Excluir", exact=True).click()
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("Nenhum registro")
                    # Seed extra records via real API for pagination/chart verification.
                    with httpx.Client(base_url=url, trust_env=False) as client:
                        client.post(
                            "/api/auth/login",
                            json={
                                "username": "admin",
                                "password": "browser-test-password",
                            },
                        )
                        for i in range(12):
                            r = client.post(
                                "/api/products",
                                json={
                                    "nome": f"Café {i:02}",
                                    "categoria": "café",
                                    "preco_venda": "8.50",
                                    "custo_unitario": "2.20",
                                    "estoque_atual": i + 2,
                                    "estoque_minimo": 5,
                                },
                            )
                            assert r.status_code == 201, r.text
                        product = client.get("/api/products?q=Matcha").json()["items"][
                            0
                        ]
                        from datetime import date, timedelta

                        for i in range(7):
                            r = client.post(
                                "/api/sales",
                                json={
                                    "data": str(date.today() - timedelta(days=i)),
                                    "metodo_pagamento": [
                                        "Pix",
                                        "Dinheiro",
                                        "Cartão de crédito",
                                    ][i % 3],
                                    "itens": [
                                        {
                                            "id_produto": product["id"],
                                            "quantidade": i % 3 + 1,
                                            "preco_unitario": "25.00",
                                        }
                                    ],
                                },
                            )
                            assert r.status_code == 201, r.text
                    page.locator('nav a[href="#products"]').click()
                    expect(page.locator(".pagination")).to_contain_text("Página 1 de 2")
                    page.locator("#next-page").click()
                    expect(page.locator(".pagination")).to_contain_text("Página 2 de 2")
                    page.locator("#page-size").select_option("25")
                    expect(page.locator("tbody tr")).to_have_count(13)
                    page.locator('[data-sort="preco_venda"]').click()
                    expect(page.locator("th[aria-sort=ascending]")).to_contain_text(
                        "Preço de venda"
                    )
                    page.locator("#search").fill("Matcha")
                    expect(page.locator("tbody tr")).to_have_count(1)
                    page.locator("#search").fill("")
                    expect(page.locator("tbody tr")).to_have_count(13)
                    page.locator("#toast").evaluate(
                        "(element) => {element.hidden = true;}"
                    )
                    page.screenshot(
                        path=str(OUTPUT / "products-desktop.png"), full_page=True
                    )
                    page.get_by_role("button", name="Editar", exact=True).first.click()
                    page.screenshot(
                        path=str(OUTPUT / "product-editor.png"), full_page=True
                    )
                    page.locator("#close-modal").click()
                    page.locator('nav a[href="#dashboard"]').click()
                    expect(page.locator(".chart-point").first).to_be_visible()
                    page.locator(".chart-point").first.hover()
                    expect(page.locator("#chart-tip")).to_contain_text("R$")
                    page.screenshot(
                        path=str(OUTPUT / "dashboard-desktop.png"), full_page=True
                    )
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.wait_for_timeout(250)
                    page.screenshot(
                        path=str(OUTPUT / "dashboard-mobile.png"), full_page=True
                    )
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    ), "Mobile viewport overflow"

                    page.locator('nav a[href="#products"]').click()
                    page.locator("#search").fill("Matcha")
                    expect(page.locator("tbody tr")).to_have_count(1)
                    page.get_by_role("button", name="Desativar", exact=True).click()
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("Inativo")
                    page.locator("#active-filter").select_option("true")
                    expect(page.locator("tbody")).to_contain_text("Nenhum registro")
                    page.locator("#active-filter").select_option("false")
                    expect(page.locator("tbody")).to_contain_text("Matcha premium")
                    page.get_by_role("button", name="Editar", exact=True).click()
                    form.locator("[name=ativo]").check()
                    page.locator("#save-button").click()
                    expect(page.locator("tbody")).to_contain_text("Nenhum registro")
                    page.locator("#mobile-logout").click()
                    expect(page.locator("#login-screen")).to_be_visible()
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    page.screenshot(
                        path=str(OUTPUT / "login-desktop.png"), full_page=True
                    )
                    assert not errors, errors
                    methods = {method for method, u in requests if "/api/" in u}
                    assert {"GET", "POST", "PUT", "DELETE"} <= methods, methods

                    (ROOT / "docs" / "VALIDACAO_HTTP.json").write_text(
                        json.dumps(
                            {
                                "methods": sorted(methods),
                                "requests": responses,
                                "uncaught_js_errors": errors,
                                "mobile_viewport_overflow": False,
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    browser.close()
                    print(
                        "Browser CRUD PASS: GET/POST/PUT/DELETE, persistence, rollback feedback, pagination, sort, charts, mobile, logout; no JS errors."
                    )
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__ == "__main__":
    run()
