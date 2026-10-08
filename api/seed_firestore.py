"""Populate Coffee BI Firestore with coherent demo business data.

Safe by default:
- never creates login users or passwords;
- cloud writes require --apply and exact --confirm-project-id;
- existing documents are not overwritten;
- --reset-demo-data deletes ONLY records created by this seed tag.

Examples:
  python -m api.seed_firestore --apply --confirm-project-id business-inteli
  python -m api.seed_firestore --reset-demo-data --apply --confirm-project-id business-inteli
"""
from __future__ import annotations

import argparse
import os
import random
from pathlib import Path
from datetime import date, timedelta
from typing import Any

from firebase_admin import firestore
from dotenv import load_dotenv

from api.firebase_db import get_firestore, next_id_in_transaction

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_TAG = "coffee-bi-demo-v1"
BUSINESS_COLLECTIONS = (
    "employees", "products", "sales", "purchases", "transactions"
)


def _money(value: float) -> int:
    return int(round(value * 100))


def build_dataset(today: date, days: int = 30) -> dict[str, list[dict[str, Any]]]:
    """Build deterministic, internally consistent data without touching Firebase."""
    days = min(max(days, 7), 90)
    rng = random.Random(20261008)

    products = [
        {"nome": "Espresso", "categoria": "Cafés", "price": 8.0, "cost": 2.65, "stock": 118, "minimum": 24},
        {"nome": "Cappuccino", "categoria": "Cafés", "price": 14.0, "cost": 5.20, "stock": 82, "minimum": 20},
        {"nome": "Latte", "categoria": "Cafés", "price": 16.0, "cost": 6.10, "stock": 71, "minimum": 18},
        {"nome": "Mocha", "categoria": "Cafés", "price": 17.5, "cost": 6.80, "stock": 54, "minimum": 15},
        {"nome": "Pão de queijo", "categoria": "Salgados", "price": 7.0, "cost": 2.35, "stock": 94, "minimum": 25},
        {"nome": "Croissant", "categoria": "Salgados", "price": 13.5, "cost": 5.00, "stock": 36, "minimum": 12},
        {"nome": "Cookie", "categoria": "Doces", "price": 9.0, "cost": 3.10, "stock": 47, "minimum": 12},
        {"nome": "Brownie", "categoria": "Doces", "price": 12.0, "cost": 4.25, "stock": 31, "minimum": 10},
        {"nome": "Suco natural", "categoria": "Bebidas", "price": 12.0, "cost": 4.40, "stock": 28, "minimum": 10},
        {"nome": "Água com gás", "categoria": "Bebidas", "price": 6.0, "cost": 2.10, "stock": 62, "minimum": 18},
    ]
    employees = [
        {"nome": "Marina Costa", "cargo": "Gerente", "email": "marina@coffeebi.demo", "telefone": "(41) 99910-2401", "ativo": True},
        {"nome": "Lucas Almeida", "cargo": "funcionario", "email": "lucas@coffeebi.demo", "telefone": "(41) 99910-2402", "ativo": True},
        {"nome": "Camila Souza", "cargo": "funcionario", "email": "camila@coffeebi.demo", "telefone": "(41) 99910-2403", "ativo": True},
    ]

    # IDs are assigned at write time. Temporary indexes connect generated records.
    sales: list[dict[str, Any]] = []
    payment_methods = ["pix", "cartão de crédito", "cartão de débito", "dinheiro"]
    weighted_products = [0, 0, 0, 1, 1, 2, 4, 4, 4, 5, 6, 7, 8, 9]
    for offset in range(days - 1, -1, -1):
        sale_date = today - timedelta(days=offset)
        # Enough history for dashboard without flooding the free tier.
        count = rng.randint(2, 5) if sale_date.weekday() < 5 else rng.randint(3, 6)
        for _ in range(count):
            item_count = rng.randint(1, 3)
            chosen: dict[int, int] = {}
            for _ in range(item_count):
                product_idx = rng.choice(weighted_products)
                chosen[product_idx] = chosen.get(product_idx, 0) + rng.randint(1, 2)
            lines = []
            total = 0
            for product_idx, quantity in chosen.items():
                product = products[product_idx]
                unit = _money(product["price"])
                subtotal = unit * quantity
                total += subtotal
                lines.append({
                    "_product_index": product_idx,
                    "nome": product["nome"],
                    "quantidade": quantity,
                    "preco_unitario_centavos": unit,
                    "subtotal_centavos": subtotal,
                })
            hour = rng.randint(8, 19)
            minute = rng.choice([0, 5, 10, 15, 20, 30, 40, 45, 50, 55])
            sales.append({
                "data": sale_date.isoformat(),
                "hora": f"{hour:02d}:{minute:02d}",
                "valor_total_centavos": total,
                "metodo_pagamento": rng.choice(payment_methods),
                "observacoes": None,
                "itens": lines,
            })

    purchases = []
    suppliers = [
        ("Grãos Serra Verde", [(0, 55), (1, 35), (2, 30), (3, 25)]),
        ("Padaria Central", [(4, 70), (5, 30), (6, 35), (7, 28)]),
        ("Bebidas Paraná", [(8, 30), (9, 60)]),
    ]
    for i, (supplier, lines_spec) in enumerate(suppliers):
        lines = []
        total = 0
        for product_idx, quantity in lines_spec:
            product = products[product_idx]
            unit = _money(product["cost"])
            subtotal = unit * quantity
            total += subtotal
            lines.append({
                "_product_index": product_idx,
                "nome": product["nome"],
                "quantidade": quantity,
                "preco_unitario_centavos": unit,
                "subtotal_centavos": subtotal,
            })
        purchases.append({
            "data": (today - timedelta(days=24 - i * 7)).isoformat(),
            "fornecedor": supplier,
            "metodo_pagamento": "pix",
            "observacoes": "Reposição de demonstração",
            "valor_total_centavos": total,
            "itens": lines,
        })

    transactions = [
        {"tipo": "saída", "descricao": "Manutenção preventiva da máquina", "categoria": "manutenção", "valor_centavos": _money(380), "data": (today - timedelta(days=18)).isoformat()},
        {"tipo": "saída", "descricao": "Campanha local em redes sociais", "categoria": "marketing", "valor_centavos": _money(220), "data": (today - timedelta(days=13)).isoformat()},
        {"tipo": "entrada", "descricao": "Coffee break corporativo", "categoria": "eventos", "valor_centavos": _money(740), "data": (today - timedelta(days=9)).isoformat()},
        {"tipo": "saída", "descricao": "Material de limpeza", "categoria": "operação", "valor_centavos": _money(146.50), "data": (today - timedelta(days=6)).isoformat()},
        {"tipo": "entrada", "descricao": "Encomenda de kits", "categoria": "eventos", "valor_centavos": _money(425), "data": (today - timedelta(days=3)).isoformat()},
    ]

    return {
        "employees": employees,
        "products": products,
        "sales": sales,
        "purchases": purchases,
        "transactions": transactions,
    }


def _reserve_ids(db, collection: str, count: int) -> list[int]:
    transaction = db.transaction()

    @firestore.transactional
    def reserve(tx):
        start, counter = next_id_in_transaction(db, tx, collection)
        tx.set(counter, {"next": start + count})
        return list(range(start, start + count))

    return reserve(transaction)


def _delete_demo_records(db) -> dict[str, int]:
    deleted: dict[str, int] = {}
    for collection in BUSINESS_COLLECTIONS:
        count = 0
        query = db.collection(collection).where("seed_tag", "==", SEED_TAG)
        for snapshot in query.stream():
            snapshot.reference.delete()
            count += 1
        deleted[collection] = count
    return deleted


def _write_dataset(db, dataset: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    ids = {
        name: _reserve_ids(db, name, len(dataset[name]))
        for name in BUSINESS_COLLECTIONS
    }
    product_ids = ids["products"]
    employee_ids = ids["employees"]

    batch = db.batch()
    writes = 0
    summary: dict[str, int] = {key: 0 for key in BUSINESS_COLLECTIONS}

    def flush_if_needed():
        nonlocal batch, writes
        if writes >= 400:
            batch.commit()
            batch = db.batch()
            writes = 0

    for ident, employee in zip(employee_ids, dataset["employees"]):
        obj = {
            "id": ident, **employee,
            "data_admissao": (date.today() - timedelta(days=180)).isoformat(),
            "seed_tag": SEED_TAG,
        }
        batch.set(db.collection("employees").document(str(ident)), obj)
        writes += 1
        summary["employees"] += 1
        flush_if_needed()

    for ident, product in zip(product_ids, dataset["products"]):
        obj = {
            "id": ident,
            "nome": product["nome"],
            "categoria": product["categoria"],
            "preco_venda_centavos": _money(product["price"]),
            "custo_unitario_centavos": _money(product["cost"]),
            "estoque_atual": product["stock"],
            "estoque_minimo": product["minimum"],
            "unidade": "un",
            "ativo": True,
            "seed_tag": SEED_TAG,
        }
        batch.set(db.collection("products").document(str(ident)), obj)
        writes += 1
        summary["products"] += 1
        flush_if_needed()

    def mapped_lines(lines):
        return [{
            "id_produto": product_ids[line["_product_index"]],
            "nome": line["nome"],
            "quantidade": line["quantidade"],
            "preco_unitario_centavos": line["preco_unitario_centavos"],
            "subtotal_centavos": line["subtotal_centavos"],
        } for line in lines]

    for ident, sale in zip(ids["sales"], dataset["sales"]):
        obj = {
            **sale,
            "id": ident,
            "funcionario_id": employee_ids[(ident - ids["sales"][0]) % len(employee_ids)],
            "itens": mapped_lines(sale["itens"]),
            "seed_tag": SEED_TAG,
        }
        batch.set(db.collection("sales").document(str(ident)), obj)
        writes += 1
        summary["sales"] += 1
        flush_if_needed()

    for ident, purchase in zip(ids["purchases"], dataset["purchases"]):
        obj = {
            **purchase, "id": ident,
            "itens": mapped_lines(purchase["itens"]),
            "seed_tag": SEED_TAG,
        }
        batch.set(db.collection("purchases").document(str(ident)), obj)
        writes += 1
        summary["purchases"] += 1
        flush_if_needed()

    for ident, tx in zip(ids["transactions"], dataset["transactions"]):
        obj = {"id": ident, **tx, "seed_tag": SEED_TAG}
        batch.set(db.collection("transactions").document(str(ident)), obj)
        writes += 1
        summary["transactions"] += 1
        flush_if_needed()

    if writes:
        batch.commit()
    return summary


def _validate_target(args) -> str:
    project = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    emulator = bool(os.getenv("FIRESTORE_EMULATOR_HOST"))
    if emulator:
        return project or "demo-coffee-bi"
    if not args.apply:
        raise SystemExit(
            "Dry-run apenas: nenhum dado foi gravado. "
            "Para gravar no Cloud Firestore use --apply --confirm-project-id ID."
        )
    if not project or args.confirm_project_id != project:
        raise SystemExit(
            "Projeto não confirmado. --confirm-project-id deve ser exatamente "
            "o FIREBASE_PROJECT_ID configurado."
        )
    return project


def _seed_counts(db) -> dict[str, int]:
    counts: dict[str, int] = {}
    for collection in BUSINESS_COLLECTIONS:
        counts[collection] = sum(
            1 for _ in db.collection(collection).where("seed_tag", "==", SEED_TAG).stream()
        )
    return counts


def main(argv: list[str] | None = None) -> int:
    # Direct execution must behave exactly like BI init: use the repository .env.
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
        print(f"Configuração carregada: {env_path}")
    else:
        load_dotenv(override=False)
        print("Aviso: .env não encontrado na raiz do projeto.")

    parser = argparse.ArgumentParser(description="Popular Coffee BI com dados de demonstração")
    parser.add_argument("--days", type=int, default=30, help="Dias de histórico (7 a 90)")
    parser.add_argument("--apply", action="store_true", help="Autorizar gravação no Firestore real")
    parser.add_argument("--confirm-project-id", help="Confirmação explícita do projeto Firebase")
    parser.add_argument(
        "--reset-demo-data", action="store_true",
        help="Excluir somente documentos marcados pelo seed antes de recriar",
    )
    args = parser.parse_args(argv)

    dataset = build_dataset(date.today(), args.days)
    print("Dados preparados:", {key: len(value) for key, value in dataset.items()})
    try:
        project = _validate_target(args)
    except SystemExit as exc:
        print(exc)
        return 2

    emulator = os.getenv("FIRESTORE_EMULATOR_HOST")
    target = f"emulador {emulator}" if emulator else "Cloud Firestore"
    print(f"Destino confirmado: projeto={project} | {target}")
    db = get_firestore()

    if args.reset_demo_data:
        print("Removendo somente dados de demonstração anteriores:", _delete_demo_records(db))

    summary = _write_dataset(db, dataset)
    verified = _seed_counts(db)
    print(f"Seed concluído no projeto {project}: {summary}")
    print(f"Verificação pós-gravação ({SEED_TAG}): {verified}")
    if any(verified[name] < summary[name] for name in BUSINESS_COLLECTIONS):
        raise RuntimeError("A verificação pós-gravação encontrou menos documentos do que o esperado.")
    print("Nenhum usuário ou senha foi criado. Use BI init para administrar acessos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
