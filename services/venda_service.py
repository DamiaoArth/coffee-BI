from sqlalchemy.orm import Session
from models.database_models import Venda, ItemVenda
from services.produto_service import ProdutoService
from typing import List, Dict
from datetime import date, datetime

class VendaService:
    @staticmethod
    def criar_venda(db: Session, data_venda: date, metodo_pagamento: str,
                   itens: List[Dict], observacoes: str = None, 
                   funcionario_id: int = None) -> Venda:
        
        valor_total = sum(item['subtotal'] for item in itens)
        
        venda = Venda(
            data=data_venda,
            hora=datetime.now().time(),
            valor_total=valor_total,
            metodo_pagamento=metodo_pagamento,
            observacoes=observacoes,
            funcionario_id=funcionario_id
        )
        db.add(venda)
        db.flush()
        
        for item in itens:
            item_venda = ItemVenda(
                id_venda=venda.id,
                id_produto=item['id_produto'],
                quantidade=item['quantidade'],
                preco_unitario=item['preco_unitario'],
                subtotal=item['subtotal']
            )
            db.add(item_venda)
            
            # Atualizar estoque
            ProdutoService.atualizar_estoque(
                db, item['id_produto'], item['quantidade'], 'remover'
            )
        
        db.commit()
        db.refresh(venda)
        return venda
    
    @staticmethod
    def listar_vendas(db: Session, data_inicio: date = None, 
                     data_fim: date = None) -> List[Venda]:
        query = db.query(Venda)
        if data_inicio:
            query = query.filter(Venda.data >= data_inicio)
        if data_fim:
            query = query.filter(Venda.data <= data_fim)
        return query.order_by(Venda.data.desc(), Venda.hora.desc()).all()
    
    @staticmethod
    def buscar_por_id(db: Session, id: int) -> Venda:
        return db.query(Venda).filter(Venda.id == id).first()
    
    @staticmethod
    def cancelar_venda(db: Session, id: int) -> bool:
        venda = VendaService.buscar_por_id(db, id)
        if venda:
            # Devolver produtos ao estoque
            for item in venda.itens:
                ProdutoService.atualizar_estoque(
                    db, item.id_produto, item.quantidade, 'adicionar'
                )
            db.delete(venda)
            db.commit()
            return True
        return False