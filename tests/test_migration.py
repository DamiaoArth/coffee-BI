from sqlalchemy import create_engine, inspect, text

from config import database


def test_additive_migration_preserves_existing_product(tmp_path, monkeypatch):
    old_engine = create_engine("sqlite:///" + str(tmp_path / "legacy.db"))
    with old_engine.begin() as connection:
        connection.execute(
            text("""CREATE TABLE produtos (
            id INTEGER PRIMARY KEY, nome VARCHAR(200), categoria VARCHAR(50),
            preco_venda NUMERIC(10,2), custo_unitario NUMERIC(10,2),
            estoque_atual INTEGER, estoque_minimo INTEGER, unidade VARCHAR(10),
            ativo BOOLEAN, data_cadastro DATETIME, data_atualizacao DATETIME
        )""")
        )
        connection.execute(
            text("""CREATE TABLE itens_venda (
            id INTEGER PRIMARY KEY, id_venda INTEGER, id_produto INTEGER,
            quantidade INTEGER, preco_unitario NUMERIC(10,2), subtotal NUMERIC(10,2)
        )""")
        )
        connection.execute(
            text(
                "INSERT INTO produtos(id,nome,estoque_atual) VALUES (7,'Café antigo',30)"
            )
        )
    monkeypatch.setattr(database, "engine", old_engine)
    database.init_db()
    database.init_db()  # Idempotent across subsequent starts.
    assert "custo_unitario" in {
        c["name"] for c in inspect(old_engine).get_columns("itens_venda")
    }
    with old_engine.connect() as connection:
        row = connection.execute(
            text("SELECT nome,estoque_atual,version FROM produtos WHERE id=7")
        ).one()
        assert tuple(row) == ("Café antigo", 30, 1)
    old_engine.dispose()


def test_postgresql_default_driver_can_be_loaded_without_psycopg3():
    for url in [
        "postgresql://test:test@localhost/test",
        "postgres://test:test@localhost/test",
    ]:
        test_engine = create_engine(database.normalize_database_url(url))
        assert test_engine.dialect.driver == "psycopg2"
        test_engine.dispose()
