from models.database_models import Venda
from services.movimento_service import cancel_movement, create_movement


class VendaService:
    @staticmethod
    def criar_venda(
        db, data_venda, metodo_pagamento, itens, observacoes=None, funcionario_id=None
    ):
        return create_movement(
            db,
            "sale",
            data_venda,
            metodo_pagamento,
            itens,
            observacoes=observacoes,
            funcionario_id=funcionario_id,
        )

    @staticmethod
    def listar_vendas(db, data_inicio=None, data_fim=None):
        query = db.query(Venda)
        if data_inicio:
            query = query.filter(Venda.data >= data_inicio)
        if data_fim:
            query = query.filter(Venda.data <= data_fim)
        return query.order_by(
            Venda.data.desc(), Venda.hora.desc(), Venda.id.desc()
        ).all()

    @staticmethod
    def buscar_por_id(db, id):
        return db.get(Venda, id)

    @staticmethod
    def cancelar_venda(db, id):
        return cancel_movement(db, "sale", id)
