from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models.database_models import Venda, ItemVenda, Produto, Transacao, Compra
from datetime import date, timedelta
import pandas as pd

class RelatorioService:
    @staticmethod
    def vendas_por_periodo(db: Session, data_inicio: date, data_fim: date) -> pd.DataFrame:
        vendas = db.query(
            Venda.data,
            func.count(Venda.id).label('qtd_vendas'),
            func.sum(Venda.valor_total).label('total')
        ).filter(
            Venda.data >= data_inicio,
            Venda.data <= data_fim
        ).group_by(Venda.data).all()
        
        return pd.DataFrame(vendas, columns=['Data', 'Quantidade', 'Total'])
    
    @staticmethod
    def produtos_mais_vendidos(db: Session, data_inicio: date, data_fim: date, 
                              top: int = 10) -> pd.DataFrame:
        resultado = db.query(
            Produto.nome,
            func.sum(ItemVenda.quantidade).label('quantidade'),
            func.sum(ItemVenda.subtotal).label('total')
        ).join(ItemVenda).join(Venda).filter(
            Venda.data >= data_inicio,
            Venda.data <= data_fim
        ).group_by(Produto.nome).order_by(
            func.sum(ItemVenda.quantidade).desc()
        ).limit(top).all()
        
        return pd.DataFrame(resultado, columns=['Produto', 'Quantidade', 'Total'])
    
    @staticmethod
    def vendas_por_categoria(db: Session, data_inicio: date, 
                            data_fim: date) -> pd.DataFrame:
        resultado = db.query(
            Produto.categoria,
            func.sum(ItemVenda.quantidade).label('quantidade'),
            func.sum(ItemVenda.subtotal).label('total')
        ).join(ItemVenda).join(Venda).filter(
            Venda.data >= data_inicio,
            Venda.data <= data_fim
        ).group_by(Produto.categoria).all()
        
        return pd.DataFrame(resultado, columns=['Categoria', 'Quantidade', 'Total'])
    
    @staticmethod
    def vendas_por_metodo_pagamento(db: Session, data_inicio: date,
                                   data_fim: date) -> pd.DataFrame:
        resultado = db.query(
            Venda.metodo_pagamento,
            func.count(Venda.id).label('quantidade'),
            func.sum(Venda.valor_total).label('total')
        ).filter(
            Venda.data >= data_inicio,
            Venda.data <= data_fim
        ).group_by(Venda.metodo_pagamento).all()
        
        return pd.DataFrame(resultado, columns=['Método', 'Quantidade', 'Total'])
    
    @staticmethod
    def fluxo_caixa(db: Session, data_inicio: date, data_fim: date) -> pd.DataFrame:
        # Vendas (entradas)
        vendas = db.query(
            Venda.data.label('data'),
            func.sum(Venda.valor_total).label('valor'),
            func.literal('Venda').label('tipo')
        ).filter(
            Venda.data >= data_inicio,
            Venda.data <= data_fim
        ).group_by(Venda.data)
        
        # Compras (saídas)
        compras = db.query(
            Compra.data.label('data'),
            func.sum(Compra.valor_total).label('valor'),
            func.literal('Compra').label('tipo')
        ).filter(
            Compra.data >= data_inicio,
            Compra.data <= data_fim
        ).group_by(Compra.data)
        
        # Outras transações
        transacoes = db.query(
            Transacao.data.label('data'),
            Transacao.valor,
            Transacao.tipo
        ).filter(
            Transacao.data >= data_inicio,
            Transacao.data <= data_fim
        )
        
        # Combinar tudo
        todas = []
        for v in vendas:
            todas.append({'data': v.data, 'entrada': float(v.valor), 'saida': 0})
        for c in compras:
            todas.append({'data': c.data, 'entrada': 0, 'saida': float(c.valor)})
        for t in transacoes:
            if t.tipo == 'entrada':
                todas.append({'data': t.data, 'entrada': float(t.valor), 'saida': 0})
            else:
                todas.append({'data': t.data, 'entrada': 0, 'saida': float(t.valor)})
        
        df = pd.DataFrame(todas)
        if not df.empty:
            df = df.groupby('data').sum().reset_index()
            df['saldo'] = df['entrada'] - df['saida']
            df['saldo_acumulado'] = df['saldo'].cumsum()
        
        return df
    
    @staticmethod
    def lucro_por_produto(db: Session, data_inicio: date, data_fim: date) -> pd.DataFrame:
        resultado = db.query(
            Produto.nome,
            func.sum(ItemVenda.quantidade).label('quantidade'),
            func.sum(ItemVenda.subtotal).label('receita'),
            func.sum(ItemVenda.quantidade * Produto.custo_unitario).label('custo')
        ).join(ItemVenda).join(Venda).filter(
            Venda.data >= data_inicio,
            Venda.data <= data_fim
        ).group_by(Produto.nome).all()
        
        df = pd.DataFrame(resultado, columns=['Produto', 'Quantidade', 'Receita', 'Custo'])
        df['Lucro'] = df['Receita'] - df['Custo']
        df['Margem %'] = (df['Lucro'] / df['Receita'] * 100).round(2)
        
        return df