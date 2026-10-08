"""Atomic stock movements shared by the HTTP API and Streamlit."""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, update

from config.clock import business_now
from models.database_models import Compra, ItemCompra, ItemVenda, Produto, Venda


def money(value):
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ValueError("Preço inválido.") from exc
    if not result.is_finite() or result < 0 or result > Decimal("99999999.99"):
        raise ValueError("Preço deve ser um número positivo.")
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_movement(db, kind, data, metodo_pagamento, itens, **extra):
    try:
        if not itens:
            raise ValueError("Adicione ao menos um produto.")
        if not metodo_pagamento or not metodo_pagamento.strip():
            raise ValueError("Informe o método de pagamento.")
        if kind == "purchase" and not extra.get("fornecedor", "").strip():
            raise ValueError("Informe o fornecedor.")
        rows = []
        total = Decimal("0")
        # Stable lock order prevents opposite-order deadlocks on PostgreSQL.
        for item in sorted(itens, key=lambda row: row["id_produto"]):
            qty = item["quantidade"]
            if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
                raise ValueError("Quantidade deve ser um inteiro maior que zero.")
            product = (
                db.query(Produto)
                .filter(Produto.id == item["id_produto"])
                .with_for_update()
                .first()
            )
            if not product or not product.ativo:
                raise ValueError("Produto inexistente ou inativo.")
            price = money(
                item.get(
                    "preco_unitario",
                    product.preco_venda if kind == "sale" else product.custo_unitario,
                )
            )
            subtotal = money(price * qty)
            if kind == "sale":
                result = db.execute(
                    update(Produto)
                    .where(
                        Produto.id == product.id,
                        Produto.ativo.is_(True),
                        Produto.estoque_atual >= qty,
                    )
                    .values(
                        estoque_atual=Produto.estoque_atual - qty,
                        version=Produto.version + 1,
                    )
                )
                if result.rowcount != 1:
                    raise ValueError(f"Estoque insuficiente para {product.nome}.")
            else:
                # Lock/read and guarded update keep cost and stock consistent.
                old_qty = product.estoque_atual
                new_qty = old_qty + qty
                if new_qty > 2147483647:
                    raise ValueError("Quantidade de estoque excede o limite suportado.")
                new_cost = money(
                    (product.custo_unitario * old_qty + price * qty) / new_qty
                )
                result = db.execute(
                    update(Produto)
                    .where(Produto.id == product.id, Produto.version == product.version)
                    .values(
                        estoque_atual=new_qty,
                        custo_unitario=new_cost,
                        version=Produto.version + 1,
                    )
                )
                if result.rowcount != 1:
                    raise ValueError(
                        "Estoque mudou durante a operação. Tente novamente."
                    )
            row = dict(
                id_produto=product.id,
                quantidade=qty,
                preco_unitario=price,
                subtotal=subtotal,
            )
            if kind == "sale":
                row["custo_unitario"] = product.custo_unitario
            rows.append(row)
            total = money(total + subtotal)
        cls, item_cls, foreign = (
            (Venda, ItemVenda, "id_venda")
            if kind == "sale"
            else (Compra, ItemCompra, "id_compra")
        )
        if kind == "sale":
            extra["hora"] = business_now().time()
        movement = cls(
            data=data,
            metodo_pagamento=metodo_pagamento.strip(),
            valor_total=total,
            **extra,
        )
        db.add(movement)
        db.flush()
        for row in rows:
            db.add(item_cls(**row, **{foreign: movement.id}))
        db.commit()
        db.refresh(movement)
        return movement
    except Exception:
        db.rollback()
        raise


def cancel_movement(db, kind, id):
    try:
        cls = Venda if kind == "sale" else Compra
        movement = db.query(cls).filter(cls.id == id).with_for_update().first()
        if not movement:
            return False
        # Claim deletion before changing stock; duplicate cancellation cannot restore twice.
        rows = [(i.id_produto, i.quantidade) for i in movement.itens]
        result = db.execute(delete(cls).where(cls.id == id))
        if result.rowcount != 1:
            db.rollback()
            return False
        for product_id, qty in sorted(rows):
            stmt = update(Produto).where(Produto.id == product_id)
            if kind == "sale":
                stmt = stmt.values(
                    estoque_atual=Produto.estoque_atual + qty,
                    version=Produto.version + 1,
                )
            else:
                stmt = stmt.where(Produto.estoque_atual >= qty).values(
                    estoque_atual=Produto.estoque_atual - qty,
                    version=Produto.version + 1,
                )
            if db.execute(stmt).rowcount != 1:
                raise ValueError("Compra não pode ser cancelada: estoque já consumido.")
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
