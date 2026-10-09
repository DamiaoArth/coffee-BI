"""Legacy UI smoke test. Requires requirements.txt; uses a temporary database."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run():
    with tempfile.TemporaryDirectory(prefix="coffee-streamlit-") as directory:
        os.environ["DATABASE_URL"] = "sqlite:///" + str(
            Path(directory) / "legacy-ui.db"
        )
        os.environ["ADMIN_PASSWORD"] = "legacy-test-password"
        os.environ["ADMIN_USERNAME"] = "admin"
        from streamlit.testing.v1 import AppTest

        from config.clock import business_today
        from config.database import SessionLocal, engine
        from models.database_models import Usuario
        from services.produto_service import ProdutoService
        from services.venda_service import VendaService

        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / "app.py")).run(timeout=20)
        assert not app.exception, app.exception
        app.text_input[0].input("admin")
        app.text_input[1].input("legacy-test-password")
        app.button[0].click().run(timeout=20)
        assert not app.exception, app.exception
        assert app.session_state["authenticated"]
        state = app.session_state["user"]
        with SessionLocal() as db:
            product = ProdutoService.criar_produto(
                db,
                nome="Café de teste",
                categoria="café",
                preco_venda=8.50,
                custo_unitario=2,
                estoque_atual=10,
            )
            VendaService.criar_venda(
                db,
                business_today(),
                "Pix",
                [{"id_produto": product.id, "quantidade": 2, "preco_unitario": 8.50}],
            )
        print("Legacy: authenticated", flush=True)
        for name in [
            "Produtos",
            "Vendas",
            "Compras",
            "Financeiro",
            "BI_Dashboard",
            "Funcionarios",
        ]:
            page = AppTest.from_file(str(root / "pages" / f"{name}.py"))
            page.session_state["authenticated"] = True
            page.session_state["user"] = state
            page.run(timeout=20)
            print("Legacy:", name, flush=True)
            assert not page.exception, (name, page.exception)
            if name == "BI_Dashboard":
                page.multiselect[0].set_value(
                    [
                        "Vendas",
                        "Produtos",
                        "Categorias",
                        "Pagamentos",
                        "Fluxo de Caixa",
                        "Lucratividade",
                    ]
                ).run(timeout=20)
                assert not page.exception, (name, page.exception)

        print("Legacy: all reports", flush=True)
        # Optional login controls must react before form submission.
        page.radio[0].set_value("➕ Cadastrar Funcionário").run(timeout=20)
        next(
            c
            for c in page.checkbox
            if c.label == "Criar usuário para acesso ao sistema"
        ).check().run(timeout=20)
        values = {
            "Nome Completo*": "Ana",
            "Nome de Usuário*": "ana",
            "Senha*": "ana-test-password",
            "Confirmar Senha*": "ana-test-password",
        }
        for input in page.text_input:
            if input.label in values:
                input.input(values[input.label])
        next(
            b for b in page.button if b.label == "💾 Cadastrar Funcionário"
        ).click().run(timeout=20)
        assert not page.exception, page.exception
        with SessionLocal() as db:
            assert (
                db.query(Usuario).filter_by(nome_usuario="ana").one().funcionario.nome
                == "Ana"
            )
        # Revocation is checked again on every rerun.
        with SessionLocal() as db:
            db.get(Usuario, state["id"]).ativo = False
            db.commit()
        page.run(timeout=20)
        assert (
            "authenticated" not in page.session_state
            or not page.session_state["authenticated"]
        )
        engine.dispose()
        print(
            "Legacy Streamlit PASS: login, six pages, populated BI, atomic employee/account creation, revocation."
        )


if __name__ == "__main__":
    run()
