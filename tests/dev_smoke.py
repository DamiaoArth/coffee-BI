"""Exercise the installed BI launcher and persistent dev DB over real HTTP.

Run after pip install -e . and -r requirements-dev.txt: python tests/dev_smoke.py.
Only temporary directories are used, including a hostile production .env.
"""

import os
import signal
import socket
import subprocess
import sysconfig
import tempfile
import time
from contextlib import closing, contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
EXECUTABLE = Path(sysconfig.get_path("scripts")) / (
    "BI.exe" if os.name == "nt" else "BI"
)


@contextmanager
def server(data_dir, working_dir, log_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "DATABASE_URL": "postgresql://invalid.example/coffee",
        "ADMIN_USERNAME": "production-admin",
        "ADMIN_PASSWORD": "production-password",
        "COOKIE_SECURE": "true",
        "CAIXA_PASSWORD": "production-password",
    }
    url = f"http://127.0.0.1:{port}"
    options = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                str(EXECUTABLE),
                "init",
                "--dev",
                "--data-dir",
                str(data_dir),
                "--port",
                str(port),
            ],
            cwd=working_dir,
            env=env,
            stdout=log,
            stderr=log,
            **options,
        )
        try:
            with httpx.Client(base_url=url, trust_env=False, timeout=2) as client:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(log_path.read_text(encoding="utf-8"))
                    try:
                        if client.get("/api/health").status_code == 200:
                            break
                    except httpx.RequestError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError(log_path.read_text(encoding="utf-8"))
                assert client.get("/").status_code == 200
                assert client.get("/docs").status_code == 200
                assert client.get("/openapi.json").status_code == 200
                for asset in [
                    "/assets/app.js",
                    "/assets/styles.css",
                    "/assets/api-docs.js",
                    "/swagger-ui/swagger-ui-bundle.js",
                    "/swagger-ui/swagger-ui.css",
                ]:
                    assert client.get(asset).status_code == 200, asset
                login = client.post(
                    "/api/auth/login", json={"username": "dev", "password": "dev12345"}
                )
                assert login.status_code == 200, login.text
                assert "Secure" not in login.headers["set-cookie"]
                assert client.get("/api/auth/me").json()["nivel_acesso"] == "admin"
                yield client
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    # BI.exe is a distlib launcher that spawns Python. A console
                    # break can stop the wrapper before its reload workers exit;
                    # stop the entire isolated test tree while the parent lives.
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )
                else:
                    os.killpg(process.pid, signal.SIGINT)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            check=False,
                        )
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)


def run():
    with tempfile.TemporaryDirectory(prefix="coffee-dev-") as temporary:
        folder = Path(temporary)
        data_dir = folder / "dados com espaço e café"
        working_dir = folder / "outra pasta"
        working_dir.mkdir()
        env_file = working_dir / ".env"
        env_contents = "DATABASE_URL=postgresql://not-running.example/production\nCOOKIE_SECURE=true\n"
        env_file.write_text(env_contents, encoding="utf-8")
        with server(data_dir, working_dir, folder / "first.log") as client:
            assert client.get("/api/products").json()["total"] == 13
            assert client.get("/api/employees").json()["total"] == 3
            created = client.post(
                "/api/products",
                json={
                    "nome": "Matcha persistente",
                    "categoria": "bebida",
                    "preco_venda": "25.00",
                    "custo_unitario": "7.00",
                    "estoque_atual": 30,
                    "estoque_minimo": 5,
                },
            )
            assert created.status_code == 201, created.text
            product = created.json()
            body = {
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
            body["nome"] = "Matcha editado"
            assert (
                client.put(
                    f"/api/products/{product['id']}",
                    json=body,
                    headers={"If-Match": str(product["version"])},
                ).status_code
                == 200
            )
            sale = client.post(
                "/api/sales",
                json={
                    "metodo_pagamento": "Pix",
                    "itens": [{"id_produto": product["id"], "quantidade": 2}],
                },
            )
            assert sale.status_code == 201, sale.text
            sale_id = sale.json()["id"]
            assert (
                client.get(f"/api/products/{product['id']}").json()["estoque_atual"]
                == 28
            )
            # Deactivation of seeded data must survive restart/reload.
            assert client.delete("/api/products/1").status_code == 204
        assert (data_dir / "dev.sqlite3").is_file()
        assert env_file.read_text(encoding="utf-8") == env_contents
        with server(data_dir, ROOT, folder / "second.log") as client:
            assert client.get("/api/products").json()["total"] == 14
            assert client.get("/api/employees").json()["total"] == 3
            persisted = client.get(f"/api/products/{product['id']}").json()
            assert (
                persisted["nome"] == "Matcha editado"
                and persisted["estoque_atual"] == 28
            )
            assert client.get("/api/products/1").json()["ativo"] is False
            assert client.get(f"/api/sales/{sale_id}").json()["valor_total"] == "50.00"
            assert client.get("/api/dashboard").json()["revenue"] == 50
            assert client.delete(f"/api/sales/{sale_id}").status_code == 204
            assert (
                client.get(f"/api/products/{product['id']}").json()["estoque_atual"]
                == 30
            )
            assert client.post("/api/auth/logout").status_code == 204
            assert client.get("/api/auth/me").status_code == 401
        # A fully emptied catalog should not be recreated from examples.
        import sqlite3

        with closing(sqlite3.connect(data_dir / "dev.sqlite3")) as db, db:
            db.execute("DELETE FROM produtos")
            db.execute("DELETE FROM funcionarios")
        with server(data_dir, working_dir, folder / "third.log") as client:
            assert client.get("/api/products").json()["total"] == 0
            assert client.get("/api/employees").json()["total"] == 0
    print(
        "BI init --dev PASS: real HTTP, local SQLite, hostile env isolation, CRUD, stock, three restarts, no duplicate/recreated seed, local API docs and logout."
    )


if __name__ == "__main__":
    run()
