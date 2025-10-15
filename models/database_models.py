from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, Date, Time,
    DateTime, ForeignKey, Text, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base

class Produto(Base):
    __tablename__ = "produtos"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False, index=True)
    categoria = Column(String(50), nullable=False, index=True)
    preco_venda = Column(Numeric(10, 2), nullable=False)
    custo_unitario = Column(Numeric(10, 2), nullable=False, default=0)
    estoque_atual = Column(Integer, nullable=False, default=0)
    estoque_minimo = Column(Integer, nullable=False, default=0)
    unidade = Column(String(10), nullable=False, default='un')
    ativo = Column(Boolean, nullable=False, default=True)
    data_cadastro = Column(DateTime, server_default=func.now())
    data_atualizacao = Column(DateTime, onupdate=func.now())
    
    # Relacionamentos
    itens_venda = relationship("ItemVenda", back_populates="produto")
    itens_compra = relationship("ItemCompra", back_populates="produto")
    
    __table_args__ = (
        CheckConstraint('preco_venda >= 0', name='check_preco_venda_positivo'),
        CheckConstraint('custo_unitario >= 0', name='check_custo_positivo'),
        CheckConstraint('estoque_atual >= 0', name='check_estoque_positivo'),
    )

class Venda(Base):
    __tablename__ = "vendas"
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False, index=True, server_default=func.current_date())
    hora = Column(Time, nullable=False, server_default=func.current_time())
    valor_total = Column(Numeric(10, 2), nullable=False)
    metodo_pagamento = Column(String(50), nullable=False)
    observacoes = Column(Text)
    funcionario_id = Column(Integer, ForeignKey("funcionarios.id"))
    criado_em = Column(DateTime, server_default=func.now())
    
    # Relacionamentos
    itens = relationship("ItemVenda", back_populates="venda", cascade="all, delete-orphan")
    funcionario = relationship("Funcionario", back_populates="vendas")
    
    __table_args__ = (
        CheckConstraint('valor_total >= 0', name='check_valor_venda_positivo'),
    )

class ItemVenda(Base):
    __tablename__ = "itens_venda"
    
    id = Column(Integer, primary_key=True, index=True)
    id_venda = Column(Integer, ForeignKey("vendas.id", ondelete="CASCADE"), nullable=False)
    id_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    
    # Relacionamentos
    venda = relationship("Venda", back_populates="itens")
    produto = relationship("Produto", back_populates="itens_venda")
    
    __table_args__ = (
        CheckConstraint('quantidade > 0', name='check_quantidade_venda_positiva'),
    )

class Compra(Base):
    __tablename__ = "compras"
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False, index=True, server_default=func.current_date())
    fornecedor = Column(String(200), nullable=False)
    valor_total = Column(Numeric(10, 2), nullable=False)
    metodo_pagamento = Column(String(50), nullable=False)
    observacoes = Column(Text)
    criado_em = Column(DateTime, server_default=func.now())
    
    # Relacionamentos
    itens = relationship("ItemCompra", back_populates="compra", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint('valor_total >= 0', name='check_valor_compra_positivo'),
    )

class ItemCompra(Base):
    __tablename__ = "itens_compra"
    
    id = Column(Integer, primary_key=True, index=True)
    id_compra = Column(Integer, ForeignKey("compras.id", ondelete="CASCADE"), nullable=False)
    id_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    
    # Relacionamentos
    compra = relationship("Compra", back_populates="itens")
    produto = relationship("Produto", back_populates="itens_compra")
    
    __table_args__ = (
        CheckConstraint('quantidade > 0', name='check_quantidade_compra_positiva'),
    )

class Transacao(Base):
    __tablename__ = "transacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(20), nullable=False, index=True)  # entrada ou saída
    descricao = Column(String(200), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    data = Column(Date, nullable=False, index=True, server_default=func.current_date())
    categoria = Column(String(50), nullable=False, index=True)
    criado_em = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("tipo IN ('entrada', 'saída')", name='check_tipo_transacao'),
        CheckConstraint('valor > 0', name='check_valor_positivo'),
    )

class Funcionario(Base):
    __tablename__ = "funcionarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    cargo = Column(String(100), nullable=False)
    telefone = Column(String(20))
    email = Column(String(200))
    ativo = Column(Boolean, nullable=False, default=True)
    data_admissao = Column(Date, server_default=func.current_date())
    criado_em = Column(DateTime, server_default=func.now())
    
    # Relacionamentos
    usuario = relationship("Usuario", back_populates="funcionario", uselist=False)
    vendas = relationship("Venda", back_populates="funcionario")

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nome_usuario = Column(String(100), nullable=False, unique=True, index=True)
    senha_hash = Column(String(255), nullable=False)
    nivel_acesso = Column(String(20), nullable=False, default='caixa')
    funcionario_id = Column(Integer, ForeignKey("funcionarios.id"), unique=True)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, server_default=func.now())
    ultimo_acesso = Column(DateTime)
    
    # Relacionamentos
    funcionario = relationship("Funcionario", back_populates="usuario")
    
    __table_args__ = (
        CheckConstraint("nivel_acesso IN ('admin', 'caixa')", name='check_nivel_acesso'),
    )