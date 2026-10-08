"""One-time SQLite/PostgreSQL -> Cloud Firestore migration.

Requires a SQL backup, a maintenance window and an EMPTY destination.
Dry-run is the default. Never inserts example records.
Original source tables and password hashes remain untouched.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class MigrationPlan:
    records: dict[str, list[dict]]
    usernames: list[tuple[str, dict]]
    counters: dict[str, int]


def read_source(url: str) -> MigrationPlan:
    # The original SQLAlchemy model imports config.database on import, so set
    # the explicit source URL BEFORE importing it. Does not call init_db().
    os.environ["DATABASE_URL"] = url
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, selectinload
    from models.database_models import (
        Compra, Funcionario, ItemCompra, ItemVenda, Produto, Transacao, Usuario, Venda,
    )
    from api.firebase_db import cents, username_key

    engine = create_engine(url, pool_pre_ping=True)
    entries: dict[str, list[dict]] = {
        "products": [], "sales": [], "purchases": [], "transactions": [],
        "employees": [], "users": [],
    }
    usernames: list[tuple[str, dict]] = []
    with Session(engine) as session:
        products = session.query(Produto).all()
        entries["products"] = [{
            "id": p.id, "nome": p.nome, "categoria": p.categoria,
            "preco_venda_centavos": cents(p.preco_venda),
            "custo_unitario_centavos": cents(p.custo_unitario),
            "estoque_atual": p.estoque_atual, "estoque_minimo": p.estoque_minimo,
            "unidade": p.unidade, "ativo": p.ativo,
        } for p in products]

        sales = session.query(Venda).options(
            selectinload(Venda.itens).selectinload(ItemVenda.produto)
        ).all()
        entries["sales"] = [{
            "id": s.id, "data": s.data.isoformat(),
            "hora": str(s.hora or "")[:5], "valor_total_centavos": cents(s.valor_total),
            "metodo_pagamento": s.metodo_pagamento,
            "observacoes": s.observacoes, "funcionario_id": s.funcionario_id,
            "itens": [{
                "id_produto": it.id_produto,
                "nome": it.produto.nome if it.produto else f"Produto #{it.id_produto}",
                "quantidade": it.quantidade,
                "preco_unitario_centavos": cents(it.preco_unitario),
                "subtotal_centavos": cents(it.subtotal),
            } for it in s.itens],
        } for s in sales]

        purchases = session.query(Compra).options(
            selectinload(Compra.itens).selectinload(ItemCompra.produto)
        ).all()
        entries["purchases"] = [{
            "id": p.id, "data": p.data.isoformat(),
            "fornecedor": p.fornecedor, "metodo_pagamento": p.metodo_pagamento,
            "observacoes": p.observacoes, "valor_total_centavos": cents(p.valor_total),
            "itens": [{
                "id_produto": it.id_produto,
                "nome": it.produto.nome if it.produto else f"Produto #{it.id_produto}",
                "quantidade": it.quantidade, "preco_unitario_centavos": cents(it.preco_unitario),
                "subtotal_centavos": cents(it.subtotal),
            } for it in p.itens],
        } for p in purchases]

        txs = session.query(Transacao).all()
        entries["transactions"] = [{
            "id": t.id, "tipo": t.tipo, "descricao": t.descricao,
            "categoria": t.categoria, "valor_centavos": cents(t.valor),
            "data": t.data.isoformat(),
        } for t in txs]

        employees = session.query(Funcionario).all()
        entries["employees"] = [{
            "id": f.id, "nome": f.nome, "cargo": f.cargo,
            "telefone": f.telefone, "email": f.email, "ativo": f.ativo,
            "data_admissao": f.data_admissao.isoformat() if f.data_admissao else None,
        } for f in employees]

        users = session.query(Usuario).all()
        entries["users"] = [{
            "id": u.id, "nome_usuario": u.nome_usuario,
            "senha_hash": u.senha_hash, "nivel_acesso": u.nivel_acesso,
            "funcionario_id": u.funcionario_id, "ativo": u.ativo,
        } for u in users]
        for u in users:
            usernames.append((username_key(u.nome_usuario), {
                "user_id": u.id, "nome_usuario": u.nome_usuario,
            }))
    engine.dispose()

    # Unlike SQL uniqueness checks, Firestore's names are case-insensitive.
    if len({key for key, _ in usernames}) != len(usernames):
        raise ValueError("A origem tem usernames duplicados (ignorando maiúsculas/minúsculas).")
    counters = {table: max((int(item["id"]) for item in rows), default=0) + 1
                for table, rows in entries.items()}
    return MigrationPlan(entries, usernames, counters)


def destination_is_empty(db) -> bool:
    return all(
        not list(db.collection(name).limit(1).stream())
        for name in (*("products", "sales", "purchases", "transactions",
                       "employees", "users", "usernames"), "_counters")
    )


def write_plan(db, plan: MigrationPlan) -> dict[str, int]:
    # Each commit contains <=400 documents, below Firestore's write batch limit.
    batch = db.batch()
    staged = 0
    total = 0
    for collection, records in plan.records.items():
        for obj in records:
            batch.set(db.collection(collection).document(str(obj["id"])), obj)
            staged += 1
            total += 1
            if staged >= 400:
                batch.commit()
                batch = db.batch()
                staged = 0
    for digest, value in plan.usernames:
        batch.set(db.collection("usernames").document(digest), value)
        staged += 1
        total += 1
        if staged >= 400:
            batch.commit()
            batch = db.batch()
            staged = 0
    for collection, ident in plan.counters.items():
        batch.set(db.collection("_counters").document(collection), {"next": ident})
        staged += 1
        total += 1
    if staged:
        batch.commit()
    return {key: len(items) for key, items in plan.records.items()}


def main():
    p = argparse.ArgumentParser(description="Migrar ERP Cafeteria para Firestore")
    p.add_argument("--apply", action="store_true",
                   help="Executa a migração; sem isso apenas lê e conta dados da origem")
    p.add_argument("--confirm-project-id",
                   help="Deve coincidir com FIREBASE_PROJECT_ID para permitir escrita")
    args = p.parse_args()

    source = os.getenv("MIGRATION_SOURCE_DATABASE_URL")
    if not source:
        raise SystemExit("Defina MIGRATION_SOURCE_DATABASE_URL apontando ao banco original.")
    plan = read_source(source)
    counts = {key: len(rows) for key, rows in plan.records.items()}
    print("Inventário da origem (sem gravar):", counts)
    if not args.apply:
        print("Dry-run concluído. Use --apply --confirm-project-id para gravar.")
        return
    project = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    if not project or args.confirm_project_id != project:
        raise SystemExit("Projeto não confirmado. Informe --confirm-project-id exato.")
    if not any(counts.values()):
        raise SystemExit("Origem vazia: migração recusada.")
    from api.firebase_db import get_firestore
    db = get_firestore()
    if not destination_is_empty(db):
        raise SystemExit("Destino NÃO está vazio. Não sobrescrever dados existentes.")
    print("Migrando para o projeto:", project)
    applied = write_plan(db, plan)
    print("Migração aplicada:", applied)
    print("IMPORTANTE: Valide registros, senhas e totais ANTES de mudar a aplicação.")


if __name__ == "__main__":
    main()
