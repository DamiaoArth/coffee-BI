from sqlalchemy.orm import Session
from models.database_models import Produto
from typing import List, Optional

class ProdutoService:
    @staticmethod
    def listar_produtos(db: Session, apenas_ativos: bool = True) -> List[Produto]:
        query = db.query(Produto)
        if apenas_ativos:
            query = query.filter(Produto.ativo == True)
        return query.order_by(Produto.nome).all()
    
    @staticmethod
    def buscar_por_id(db: Session, id: int) -> Optional[Produto]:
        return db.query(Produto).filter(Produto.id == id).first()
    
    @staticmethod
    def criar_produto(db: Session, **dados) -> Produto:
        produto = Produto(**dados)
        db.add(produto)
        db.commit()
        db.refresh(produto)
        return produto
    
    @staticmethod
    def atualizar_produto(db: Session, id: int, **dados) -> Optional[Produto]:
        produto = ProdutoService.buscar_por_id(db, id)
        if produto:
            for key, value in dados.items():
                setattr(produto, key, value)
            db.commit()
            db.refresh(produto)
        return produto
    
    @staticmethod
    def deletar_produto(db: Session, id: int) -> bool:
        produto = ProdutoService.buscar_por_id(db, id)
        if produto:
            produto.ativo = False
            db.commit()
            return True
        return False
    
    @staticmethod
    def produtos_estoque_baixo(db: Session) -> List[Produto]:
        return db.query(Produto).filter(
            Produto.ativo == True,
            Produto.estoque_atual <= Produto.estoque_minimo
        ).all()
    
    @staticmethod
    def atualizar_estoque(db: Session, id_produto: int, quantidade: int, 
                         operacao: str = 'adicionar') -> bool:
        produto = ProdutoService.buscar_por_id(db, id_produto)
        if produto:
            if operacao == 'adicionar':
                produto.estoque_atual += quantidade
            elif operacao == 'remover':
                if produto.estoque_atual >= quantidade:
                    produto.estoque_atual -= quantidade
                else:
                    return False
            db.commit()
            return True
        return False