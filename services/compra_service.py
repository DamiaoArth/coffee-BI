from sqlalchemy.orm import Session
from models.database_models import Compra, ItemCompra
from services.produto_service import ProdutoService
from typing import List, Dict
from datetime import date

class CompraService:
    @staticmethod
    def criar_compra(db: Session, data_compra: date, fornecedor: str,
                    metodo_pagamento: str, itens: List[Dict], 
                    observacoes: str = None) -> Compra:
        
        valor_total = sum(item['subtotal'] for item in itens)
        
        compra = Compra(
            data=data_compra,
            fornecedor=fornecedor,
            valor_total=valor_total,
            metodo_pagamento=metodo_pagamento,
            observacoes=observacoes
        )
        db.add(compra)
        db.flush()
        
        for item in itens:
            item_compra = ItemCompra(
                id_compra=compra.id,
                id_produto=item['id_produto'],
                quantidade=item['quantidade'],
                preco_unitario=item['preco_unitario'],
                subtotal=item['subtotal']
            )
            db.add(item_compra)
            
            # Atualizar estoque
            ProdutoService.atualizar_estoque(
                db, item['id_produto'], item['quantidade'], 'adicionar'
            )
            
            # Atualizar custo unitário (média ponderada)
            produto = ProdutoService.buscar_por_id(db, item['id_produto'])
            if produto:
                estoque_anterior = produto.estoque_atual - item['quantidade']
                if estoque_anterior > 0:
                    custo_total_anterior = produto.custo_unitario * estoque_anterior
                    custo_total_novo = item['preco_unitario'] * item['quantidade']
                    produto.custo_unitario = (
                        (custo_total_anterior + custo_total_novo) / 
                        produto.estoque_atual
                    )
                else:
                    produto.custo_unitario = item['preco_unitario']
        
        db.commit()
        db.refresh(compra)
        return compra
    
    @staticmethod
    def listar_compras(db: Session, data_inicio: date = None,
                      data_fim: date = None) -> List[Compra]:
        query = db.query(Compra)
        if data_inicio:
            query = query.filter(Compra.data >= data_inicio)
        if data_fim:
            query = query.filter(Compra.data <= data_fim)
        return query.order_by(Compra.data.desc()).all()
