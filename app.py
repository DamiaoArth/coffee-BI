import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.icons import icon, material  # noqa: E402
from ui.theme import apply_theme  # noqa: E402

# Ler a sessão antes de renderizar permite abrir a tela de login sem a barra
# lateral, que só faz sentido depois da autenticação.
_autenticado = bool(st.session_state.get("authenticated"))

st.set_page_config(
    page_title="ERP Cafeteria",
    page_icon=material("coffee"),
    layout="wide",
    initial_sidebar_state="expanded" if _autenticado else "collapsed",
)
apply_theme(login=not _autenticado)

from config.database import SessionLocal, init_db  # noqa: E402
from models.database_models import Usuario  # noqa: E402
from services.auth_service import AuthService  # noqa: E402
from services.produto_service import ProdutoService  # noqa: E402
from services.relatorio_service import RelatorioService  # noqa: E402
from ui import charts  # noqa: E402
from ui.components import (  # noqa: E402
    empty_state,
    kpi_card,
    kpi_row,
    notice,
    page_header,
    section,
)
from ui.format import brl, data_br, num, plural  # noqa: E402
from ui.page import sidebar_shell  # noqa: E402

USUARIOS_PADRAO = [
    {"nome_usuario": "admin", "senha": "admin123", "nivel_acesso": "admin"},
    {"nome_usuario": "gerente", "senha": "gerente123", "nivel_acesso": "Gerente"},
    {"nome_usuario": "funcionario", "senha": "funcionario123", "nivel_acesso": "funcionario"},
]


@st.cache_resource(show_spinner=False)
def initialize_database() -> list:
    """Cria o schema e as contas padrão. Retorna as contas criadas nesta execução."""
    init_db()
    criados = []
    db = SessionLocal()
    try:
        for dados in USUARIOS_PADRAO:
            existe = (
                db.query(Usuario)
                .filter(Usuario.nome_usuario == dados["nome_usuario"])
                .first()
            )
            if not existe:
                AuthService.criar_usuario(db=db, **dados)
                criados.append(dados["nome_usuario"])
    finally:
        db.close()
    return criados


st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("user", None)
contas_criadas = initialize_database()


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #
def login_page():
    st.markdown(
        '<div style="height:6vh"></div>'
        '<div style="display:flex;flex-direction:column;align-items:center;gap:4px;">'
        '<div class="erp-head-mark" style="width:52px;height:52px;">'
        f'{icon("coffee", 26)}</div>'
        '<p class="erp-head-eyebrow" style="margin:10px 0 0;">'
        "Gestão e inteligência de negócio</p>"
        '<h1 class="erp-head-title" style="font-size:1.7rem;">ERP Cafeteria</h1>'
        "</div>",
        unsafe_allow_html=True,
    )

    _, meio, _ = st.columns([1, 1.25, 1])
    with meio:
        with st.form("login"):
            usuario = st.text_input("Usuário", placeholder="Seu nome de usuário")
            senha = st.text_input("Senha", type="password", placeholder="Sua senha")
            entrar = st.form_submit_button(
                "Entrar", width="stretch", type="primary", icon=material("login")
            )

        if entrar:
            if not usuario or not senha:
                notice("Preencha usuário e senha para continuar.", "warning")
                return

            db = SessionLocal()
            try:
                user = AuthService.authenticate(db, usuario, senha)
                if user is None:
                    notice("Usuário ou senha incorretos. Verifique e tente de novo.", "error")
                    return
                st.session_state.user = {
                    "id": user.id,
                    "username": user.nome_usuario,
                    "nivel_acesso": user.nivel_acesso,
                    "funcionario_id": user.funcionario_id,
                }
            finally:
                db.close()

            st.session_state.authenticated = True
            st.rerun()

        if contas_criadas:
            notice(
                "Primeiro acesso. Contas criadas: <strong>"
                + "</strong>, <strong>".join(contas_criadas)
                + "</strong>. A senha inicial é o nome do usuário seguido de 123. "
                "Troque-a em Funcionários depois de entrar.",
                "info",
                icon_name="key",
            )


# --------------------------------------------------------------------------- #
# Painel geral
# --------------------------------------------------------------------------- #
def dashboard():
    user = st.session_state.user
    page_header(
        "dashboard",
        "Visão geral",
        "Resultado do mês corrente, estoque e vendas recentes.",
    )

    sidebar_shell(user)

    db = SessionLocal()
    try:
        hoje = date.today()
        inicio_mes = hoje.replace(day=1)

        vendas_mes = RelatorioService.vendas_por_periodo(db, inicio_mes, hoje)
        total_mes = float(vendas_mes["Total"].sum()) if not vendas_mes.empty else 0.0
        qtd_mes = int(vendas_mes["Quantidade"].sum()) if not vendas_mes.empty else 0

        vendas_hoje = RelatorioService.vendas_por_periodo(db, hoje, hoje)
        total_hoje = float(vendas_hoje["Total"].sum()) if not vendas_hoje.empty else 0.0
        qtd_hoje = int(vendas_hoje["Quantidade"].sum()) if not vendas_hoje.empty else 0

        produtos_baixo = ProdutoService.produtos_estoque_baixo(db)
        produtos_ativos = len(ProdutoService.listar_produtos(db))

        kpi_row(
            [
                kpi_card(
                    "Faturamento do mês",
                    brl(total_mes),
                    "money",
                    delta=plural(qtd_mes, "venda", "vendas"),
                    delta_tone="brand",
                    hint=f"desde {data_br(inicio_mes)}",
                    tone="brand",
                ),
                kpi_card(
                    "Vendas de hoje",
                    brl(total_hoje),
                    "receipt",
                    delta=plural(qtd_hoje, "venda", "vendas"),
                    delta_tone="pos" if qtd_hoje else "neutral",
                    tone="pos",
                ),
                kpi_card(
                    "Estoque em alerta",
                    num(len(produtos_baixo)),
                    "alert",
                    delta="repor" if produtos_baixo else "tudo certo",
                    delta_tone="neg" if produtos_baixo else "pos",
                    tone="neg" if produtos_baixo else "neutral",
                ),
                kpi_card("Produtos ativos", num(produtos_ativos), "box", hint="no catálogo"),
            ]
        )

        if produtos_baixo:
            section("alert", "Reposição necessária")
            notice(
                f"<strong>{plural(len(produtos_baixo), 'produto está', 'produtos estão')}"
                " no nível mínimo ou abaixo dele.</strong>",
                "warning",
            )
            with st.expander("Ver itens", icon=material("box")):
                for p in produtos_baixo:
                    st.markdown(
                        f"**{p.nome}** — {p.estoque_atual} {p.unidade} "
                        f"(mínimo {p.estoque_minimo} {p.unidade})"
                    )

        section("line_chart", "Vendas dos últimos 7 dias")
        semana = RelatorioService.vendas_por_periodo(db, hoje - timedelta(days=6), hoje)
        if semana.empty:
            empty_state(
                "line_chart",
                "Sem vendas na última semana",
                "Registre uma venda para acompanhar a evolução por aqui.",
            )
        else:
            st.plotly_chart(
                charts.area_line(
                    semana["Data"], semana["Total"], "Faturamento", "Faturamento diário"
                ),
                width="stretch",
            )

        col_a, col_b = st.columns(2)
        with col_a:
            section("trophy", "Produtos mais vendidos")
            top = RelatorioService.produtos_mais_vendidos(db, inicio_mes, hoje, top=5)
            if top.empty:
                empty_state("box", "Sem dados no mês")
            else:
                st.plotly_chart(
                    charts.donut(top["Produto"], top["Quantidade"], "Participação por volume"),
                    width="stretch",
                )

        with col_b:
            section("card", "Formas de pagamento")
            metodos = RelatorioService.vendas_por_metodo_pagamento(db, inicio_mes, hoje)
            if metodos.empty:
                empty_state("card", "Sem dados no mês")
            else:
                st.plotly_chart(
                    charts.hbar(metodos["Método"], metodos["Total"], "Faturamento por método"),
                    width="stretch",
                )

        section("dashboard", "Atalhos")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.page_link(
                "pages/Vendas.py",
                label="Registrar venda",
                icon=material("cart"),
                width="stretch",
            )
        with c2:
            st.page_link(
                "pages/Produtos.py",
                label="Gerenciar produtos",
                icon=material("box"),
                width="stretch",
            )
        with c3:
            st.page_link(
                "pages/BI_Dashboard.py",
                label="Abrir relatórios",
                icon=material("analytics"),
                width="stretch",
            )

    except Exception as erro:  # superfície de UI
        notice(f"Não foi possível carregar o painel: {erro}", "error")
    finally:
        db.close()


if st.session_state.authenticated:
    dashboard()
else:
    login_page()
