"""
Script de Inicialização do Banco de Dados
Este script cria o banco de dados, tabelas e dados iniciais
"""

from datetime import date

from config.database import SessionLocal, init_db
from models.database_models import Funcionario, Produto


def criar_produtos_exemplo():
    """Cria produtos de exemplo para demonstração"""
    db = SessionLocal()

    produtos_exemplo = [
        # Bebidas
        {
            "nome": "Café Expresso",
            "categoria": "café",
            "preco_venda": 5.00,
            "custo_unitario": 1.50,
            "estoque_atual": 100,
            "estoque_minimo": 20,
            "unidade": "un",
        },
        {
            "nome": "Cappuccino",
            "categoria": "café",
            "preco_venda": 8.00,
            "custo_unitario": 2.50,
            "estoque_atual": 80,
            "estoque_minimo": 15,
            "unidade": "un",
        },
        {
            "nome": "Café com Leite",
            "categoria": "café",
            "preco_venda": 6.00,
            "custo_unitario": 2.00,
            "estoque_atual": 90,
            "estoque_minimo": 20,
            "unidade": "un",
        },
        {
            "nome": "Suco de Laranja",
            "categoria": "bebida",
            "preco_venda": 7.00,
            "custo_unitario": 2.50,
            "estoque_atual": 50,
            "estoque_minimo": 10,
            "unidade": "un",
        },
        {
            "nome": "Água Mineral",
            "categoria": "bebida",
            "preco_venda": 3.00,
            "custo_unitario": 1.00,
            "estoque_atual": 100,
            "estoque_minimo": 30,
            "unidade": "un",
        },
        {
            "nome": "Refrigerante Lata",
            "categoria": "bebida",
            "preco_venda": 5.00,
            "custo_unitario": 2.00,
            "estoque_atual": 60,
            "estoque_minimo": 20,
            "unidade": "un",
        },
        # Lanches
        {
            "nome": "Pão de Queijo",
            "categoria": "lanche",
            "preco_venda": 4.00,
            "custo_unitario": 1.50,
            "estoque_atual": 40,
            "estoque_minimo": 10,
            "unidade": "un",
        },
        {
            "nome": "Croissant",
            "categoria": "lanche",
            "preco_venda": 6.00,
            "custo_unitario": 2.00,
            "estoque_atual": 30,
            "estoque_minimo": 10,
            "unidade": "un",
        },
        {
            "nome": "Sanduíche Natural",
            "categoria": "lanche",
            "preco_venda": 12.00,
            "custo_unitario": 5.00,
            "estoque_atual": 20,
            "estoque_minimo": 5,
            "unidade": "un",
        },
        {
            "nome": "Bolo de Chocolate",
            "categoria": "sobremesa",
            "preco_venda": 8.00,
            "custo_unitario": 3.00,
            "estoque_atual": 15,
            "estoque_minimo": 5,
            "unidade": "un",
        },
        # Insumos
        {
            "nome": "Café em Grão",
            "categoria": "insumo",
            "preco_venda": 0.00,
            "custo_unitario": 35.00,
            "estoque_atual": 10,
            "estoque_minimo": 3,
            "unidade": "kg",
        },
        {
            "nome": "Leite Integral",
            "categoria": "insumo",
            "preco_venda": 0.00,
            "custo_unitario": 4.50,
            "estoque_atual": 20,
            "estoque_minimo": 5,
            "unidade": "l",
        },
        {
            "nome": "Açúcar",
            "categoria": "insumo",
            "preco_venda": 0.00,
            "custo_unitario": 3.00,
            "estoque_atual": 15,
            "estoque_minimo": 5,
            "unidade": "kg",
        },
    ]

    try:
        for produto_data in produtos_exemplo:
            # Verificar se produto já existe
            existe = (
                db.query(Produto).filter(Produto.nome == produto_data["nome"]).first()
            )

            if not existe:
                produto = Produto(**produto_data)
                db.add(produto)

        db.commit()
        print("✅ Produtos de exemplo criados com sucesso!")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar produtos: {str(e)}")
        return False
    finally:
        db.close()


def criar_funcionarios_exemplo():
    """Cria funcionários de exemplo"""
    db = SessionLocal()

    funcionarios_exemplo = [
        {
            "nome": "Maria Silva",
            "cargo": "gerente",
            "telefone": "(41) 99999-0001",
            "email": "maria.silva@cafeteria.com",
            "data_admissao": date(2024, 1, 15),
        },
        {
            "nome": "João Santos",
            "cargo": "barista",
            "telefone": "(41) 99999-0002",
            "email": "joao.santos@cafeteria.com",
            "data_admissao": date(2024, 3, 1),
        },
        {
            "nome": "Ana Costa",
            "cargo": "caixa",
            "telefone": "(41) 99999-0003",
            "email": "ana.costa@cafeteria.com",
            "data_admissao": date(2024, 4, 10),
        },
    ]

    try:
        for func_data in funcionarios_exemplo:
            # Verificar se funcionário já existe
            existe = (
                db.query(Funcionario)
                .filter(Funcionario.nome == func_data["nome"])
                .first()
            )

            if not existe:
                funcionario = Funcionario(**func_data)
                db.add(funcionario)

        db.commit()
        print("✅ Funcionários de exemplo criados com sucesso!")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar funcionários: {str(e)}")
        return False
    finally:
        db.close()


def criar_usuarios_sistema():
    """Bootstrap configured users without embedding passwords."""
    from config.bootstrap import bootstrap_users

    try:
        bootstrap_users()
        return True
    except ValueError as exc:
        print(f"Erro: {exc}")
        return False


def inicializar_sistema(criar_dados_exemplo=True):
    """
    Inicializa o sistema completo

    Args:
        criar_dados_exemplo: Se True, cria produtos e funcionários de exemplo
    """
    print("=" * 60)
    print("🚀 INICIALIZANDO SISTEMA ERP CAFETERIA")
    print("=" * 60)

    # Criar estrutura do banco
    print("\n📊 Criando estrutura do banco de dados...")
    try:
        init_db()
        print("✅ Estrutura do banco criada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao criar estrutura: {str(e)}")
        return False

    # Criar usuários do sistema
    print("\n👤 Criando usuários do sistema...")
    if not criar_usuarios_sistema():
        return False

    # Criar dados de exemplo (opcional)
    if criar_dados_exemplo:
        print("\n📦 Criando dados de exemplo...")

        criar_produtos_exemplo()
        criar_funcionarios_exemplo()

    print("\n" + "=" * 60)
    print("✅ SISTEMA INICIALIZADO COM SUCESSO!")
    print("=" * 60)
    print("Usuários configurados em ADMIN_USERNAME/ADMIN_PASSWORD e CAIXA_PASSWORD.")
    print("Nova interface: uvicorn api.main:app --reload")
    print("Interface Streamlit: streamlit run app.py")

    return True


def resetar_banco():
    """
    CUIDADO: Remove todo o banco de dados e recria do zero
    """
    print("⚠️  ATENÇÃO: Esta ação irá DELETAR todos os dados!")
    confirmacao = input("Digite 'CONFIRMAR' para prosseguir: ")

    if confirmacao == "CONFIRMAR":
        try:
            from pathlib import Path

            from config.database import engine

            if engine.dialect.name != "sqlite":
                raise ValueError("Reset automático disponível apenas para SQLite.")
            target = engine.url.database
            engine.dispose()
            if target and target != ":memory:":
                Path(target).unlink(missing_ok=True)
                print("✅ Banco configurado removido!")

            # Reinicializar
            inicializar_sistema(criar_dados_exemplo=True)
        except Exception as e:
            print(f"❌ Erro ao resetar banco: {str(e)}")
    else:
        print("❌ Operação cancelada!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset":
            resetar_banco()
        elif sys.argv[1] == "--no-examples":
            inicializar_sistema(criar_dados_exemplo=False)
        else:
            print("Opções disponíveis:")
            print("  python init_db.py           - Inicializa com dados de exemplo")
            print("  python init_db.py --no-examples - Inicializa sem dados de exemplo")
            print("  python init_db.py --reset   - Reseta o banco (CUIDADO!)")
    else:
        inicializar_sistema(criar_dados_exemplo=True)
