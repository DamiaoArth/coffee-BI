from models.database_models import Compra
from services.movimento_service import cancel_movement, create_movement


class CompraService:
    @staticmethod
    def criar_compra(
        db, data_compra, fornecedor, metodo_pagamento, itens, observacoes=None
    ):
        return create_movement(
            db,
            "purchase",
            data_compra,
            metodo_pagamento,
            itens,
            fornecedor=fornecedor,
            observacoes=observacoes,
        )

    @staticmethod
    def listar_compras(db, data_inicio=None, data_fim=None):
        query = db.query(Compra)
        if data_inicio:
            query = query.filter(Compra.data >= data_inicio)
        if data_fim:
            query = query.filter(Compra.data <= data_fim)
        return query.order_by(Compra.data.desc(), Compra.id.desc()).all()

    @staticmethod
    def cancelar_compra(db, id):
        return cancel_movement(db, "purchase", id)
