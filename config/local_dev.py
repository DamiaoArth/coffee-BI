"""First-run sample catalog for the isolated SQLite development database."""

import os
from datetime import date
from decimal import Decimal

from sqlalchemy import Column, DateTime, String, func

from config.database import Base, SessionLocal, engine
from models.database_models import Funcionario, Produto


class LocalSetup(Base):
    __tablename__ = "coffee_local_setup"
    name = Column(String(50), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())


# Prices and stock are examples; no artificial sales/financial history.
PRODUCTS = [
    ("Café Expresso", "café", "5.00", "1.50", 100, 20, "un"),
    ("Cappuccino", "café", "8.00", "2.50", 80, 15, "un"),
    ("Café com Leite", "café", "6.00", "2.00", 90, 20, "un"),
    ("Suco de Laranja", "bebida", "7.00", "2.50", 50, 10, "un"),
    ("Água Mineral", "bebida", "3.00", "1.00", 100, 30, "un"),
    ("Refrigerante Lata", "bebida", "5.00", "2.00", 60, 20, "un"),
    ("Pão de Queijo", "lanche", "4.00", "1.50", 40, 10, "un"),
    ("Croissant", "lanche", "6.00", "2.00", 30, 10, "un"),
    ("Sanduíche Natural", "lanche", "12.00", "5.00", 20, 5, "un"),
    ("Bolo de Chocolate", "sobremesa", "8.00", "3.00", 15, 5, "un"),
    ("Café em Grão", "insumo", "0.00", "35.00", 10, 3, "kg"),
    ("Leite Integral", "insumo", "0.00", "4.50", 20, 5, "l"),
    ("Açúcar", "insumo", "0.00", "3.00", 15, 5, "kg"),
]


def prepare_local_database():
    if os.getenv("COFFEE_BI_MODE") != "dev":
        return
    if engine.dialect.name != "sqlite" or engine.url.database in {None, "", ":memory:"}:
        raise RuntimeError("O modo dev exige um arquivo SQLite local.")
    LocalSetup.__table__.create(engine, checkfirst=True)
    with SessionLocal.begin() as db:
        if db.get(LocalSetup, "catalog-v1"):
            return
        # Existing data in an explicitly chosen local folder is retained.
        if not db.query(Produto).first() and not db.query(Funcionario).first():
            db.add_all(
                [
                    Produto(
                        nome=name,
                        categoria=category,
                        preco_venda=Decimal(price),
                        custo_unitario=Decimal(cost),
                        estoque_atual=stock,
                        estoque_minimo=minimum,
                        unidade=unit,
                    )
                    for name, category, price, cost, stock, minimum, unit in PRODUCTS
                ]
            )
            db.add_all(
                [
                    Funcionario(nome=name, cargo=role, data_admissao=date(2024, 1, 15))
                    for name, role in [
                        ("Maria Silva", "gerente"),
                        ("João Santos", "barista"),
                        ("Ana Costa", "caixa"),
                    ]
                ]
            )
        db.add(LocalSetup(name="catalog-v1"))
