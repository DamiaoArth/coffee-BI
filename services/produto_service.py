from sqlalchemy import update

from models.database_models import Produto
from services.movimento_service import money

FIELDS = {
    "nome",
    "categoria",
    "preco_venda",
    "custo_unitario",
    "estoque_atual",
    "estoque_minimo",
    "unidade",
    "ativo",
}


def validate(data):
    if set(data) - FIELDS:
        raise ValueError("Campo de produto inválido.")
    for field, size in [("nome", 200), ("categoria", 50), ("unidade", 10)]:
        if field in data:
            if (
                not isinstance(data[field], str)
                or not data[field].strip()
                or len(data[field].strip()) > size
            ):
                raise ValueError(
                    f"{field}: informe um texto válido de até {size} caracteres."
                )
            data[field] = data[field].strip()
    for field in ("preco_venda", "custo_unitario"):
        if field in data:
            data[field] = money(data[field])
    for field in ("estoque_atual", "estoque_minimo"):
        if field in data and (
            isinstance(data[field], bool)
            or not isinstance(data[field], int)
            or data[field] < 0
        ):
            raise ValueError("Estoque deve ser um inteiro não negativo.")
    return data


def commit(db, row):
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        raise


class ProdutoService:
    @staticmethod
    def listar_produtos(db, apenas_ativos=True):
        query = db.query(Produto)
        if apenas_ativos:
            query = query.filter(Produto.ativo.is_(True))
        return query.order_by(Produto.nome, Produto.id).all()

    @staticmethod
    def buscar_por_id(db, id):
        return db.get(Produto, id)

    @staticmethod
    def criar_produto(db, **dados):
        return commit(db, Produto(**validate(dados)))

    @staticmethod
    def atualizar_produto(db, id, **dados):
        data = validate(dados)
        produto = db.get(Produto, id)
        if produto:
            for key, value in data.items():
                setattr(produto, key, value)
            produto.version += 1
            commit(db, produto)
        return produto

    @staticmethod
    def deletar_produto(db, id):
        return ProdutoService.atualizar_produto(db, id, ativo=False) is not None

    @staticmethod
    def produtos_estoque_baixo(db):
        return (
            db.query(Produto)
            .filter(
                Produto.ativo.is_(True), Produto.estoque_atual <= Produto.estoque_minimo
            )
            .order_by(Produto.estoque_atual, Produto.nome)
            .all()
        )

    @staticmethod
    def atualizar_estoque(db, id_produto, quantidade, operacao="adicionar"):
        if (
            isinstance(quantidade, bool)
            or not isinstance(quantidade, int)
            or quantidade < 0
            or operacao not in {"adicionar", "remover"}
        ):
            raise ValueError("Informe quantidade e operação de estoque válidas.")
        try:
            statement = update(Produto).where(
                Produto.id == id_produto, Produto.ativo.is_(True)
            )
            if operacao == "remover":
                statement = statement.where(Produto.estoque_atual >= quantidade)
            delta = quantidade if operacao == "adicionar" else -quantidade
            result = db.execute(
                statement.values(
                    estoque_atual=Produto.estoque_atual + delta,
                    version=Produto.version + 1,
                )
            )
            db.commit()
            return result.rowcount == 1
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def atualizar_estoque_e_minimo(db, id, estoque_atual, estoque_minimo):
        return (
            ProdutoService.atualizar_produto(
                db, id, estoque_atual=estoque_atual, estoque_minimo=estoque_minimo
            )
            is not None
        )

    @staticmethod
    def atualizar_estoques(db, rows):
        """All-or-nothing bulk edit used by the legacy stock editor."""
        try:
            for row in rows:
                data = validate(
                    {
                        "estoque_atual": int(row["estoque_atual"]),
                        "estoque_minimo": int(row["estoque_minimo"]),
                    }
                )
                produto = db.get(Produto, int(row["id"]))
                if not produto:
                    raise ValueError("Produto não encontrado.")
                for key, value in data.items():
                    setattr(produto, key, value)
                produto.version += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
