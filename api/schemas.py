from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from config.clock import business_today

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
Count = Annotated[int, Field(strict=True, ge=0, le=2147483647)]


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Payload):
    username: Text
    password: Annotated[str, Field(min_length=1, max_length=72)]


class Product(Payload):
    nome: Text
    categoria: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
    ]
    preco_venda: Money
    custo_unitario: Money = Decimal("0")
    estoque_atual: Count = 0
    estoque_minimo: Count = 0
    unidade: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)
    ] = "un"
    ativo: bool = True


class Item(Payload):
    id_produto: Annotated[int, Field(gt=0, strict=True, le=2147483647)]
    quantidade: Annotated[int, Field(gt=0, strict=True, le=2147483647)]
    preco_unitario: Money | None = None


class Movement(Payload):
    data: date = Field(default_factory=business_today)
    metodo_pagamento: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
    ]
    itens: Annotated[list[Item], Field(min_length=1, max_length=100)]
    observacoes: Annotated[str, Field(max_length=2000)] | None = None


class Purchase(Movement):
    fornecedor: Text


class Employee(Payload):
    nome: Text
    cargo: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    telefone: Annotated[str, Field(max_length=20)] | None = None
    email: Annotated[str, Field(max_length=200)] | None = None
    data_admissao: date = Field(default_factory=business_today)
    ativo: bool = True


class Transaction(Payload):
    tipo: Literal["entrada", "saída"]
    descricao: Text
    valor: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
    data: date = Field(default_factory=business_today)
    categoria: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
    ]
