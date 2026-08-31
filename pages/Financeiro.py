import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.page import ROLES_GESTAO, setup_page  # noqa: E402

user = setup_page(
    title="Financeiro",
    icon_name="wallet",
    heading="Financeiro",
    subtitle="Lançamentos manuais, extrato e análise de entradas e saídas.",
    roles=ROLES_GESTAO,
)

from config.database import SessionLocal  # noqa: E402
from models.database_models import Transacao  # noqa: E402
from ui import charts  # noqa: E402
from ui.components import (  # noqa: E402
    data_table,
    download_csv,
    empty_state,
    kpi_card,
    kpi_row,
    notice,
    section,
    sidebar_nav,
)
from ui.format import brl, data_br, num, plural  # noqa: E402
from ui.icons import material  # noqa: E402

CATEGORIAS_ENTRADA = ["venda", "investimento", "empréstimo", "doação", "outro"]
CATEGORIAS_SAIDA = [
    "aluguel", "água", "luz", "internet", "telefone", "salário",
    "insumo", "manutenção", "marketing", "impostos", "outro",
]

with st.sidebar:
    opcao = sidebar_nav(
        [
            ("nova", "Novo lançamento", "plus"),
            ("extrato", "Extrato", "list"),
            ("analise", "Análise", "analytics"),
        ],
        state_key="nav_financeiro",
    )

db = SessionLocal()


def carregar(inicio: date, fim: date):
    return (
        db.query(Transacao)
        .filter(Transacao.data >= inicio, Transacao.data <= fim)
        .order_by(Transacao.data.desc())
        .all()
    )


try:
    # ------------------------------------------------------------- novo lançamento
    if opcao == "nova":
        col_form, col_lado = st.columns([1.4, 1], gap="large")

        with col_form:
            section("plus", "Novo lançamento")

            tipo = st.radio(
                "Tipo",
                ["entrada", "saída"],
                horizontal=True,
                format_func=str.capitalize,
                key="tipo_transacao",
            )

            with st.form("nova_transacao", clear_on_submit=True):
                descricao = st.text_input(
                    "Descrição*", placeholder="Ex.: conta de luz de agosto"
                )
                c1, c2 = st.columns(2)
                with c1:
                    valor = st.number_input(
                        "Valor (R$)*", min_value=0.01, value=100.00, step=10.00, format="%.2f"
                    )
                    data_transacao = st.date_input(
                        "Data*", value=date.today(), format="DD/MM/YYYY"
                    )
                with c2:
                    categoria = st.selectbox(
                        "Categoria*",
                        CATEGORIAS_ENTRADA if tipo == "entrada" else CATEGORIAS_SAIDA,
                    )

                registrar = st.form_submit_button(
                    "Registrar lançamento",
                    width="stretch",
                    type="primary",
                    icon=material("save"),
                )

            if registrar:
                if not descricao.strip():
                    notice("Informe uma descrição para o lançamento.", "warning")
                else:
                    try:
                        db.add(
                            Transacao(
                                tipo=tipo,
                                descricao=descricao.strip(),
                                valor=valor,
                                data=data_transacao,
                                categoria=categoria,
                            )
                        )
                        db.commit()
                        st.toast("Lançamento registrado.", icon=material("check"))
                        st.rerun()
                    except Exception as erro:
                        db.rollback()
                        notice(f"Não foi possível registrar: {erro}", "error")

        with col_lado:
            section("clock", "Movimento de hoje")
            hoje = date.today()
            do_dia = carregar(hoje, hoje)

            entradas = sum(float(t.valor) for t in do_dia if t.tipo == "entrada")
            saidas = sum(float(t.valor) for t in do_dia if t.tipo == "saída")
            saldo = entradas - saidas

            kpi_row(
                [
                    kpi_card("Entradas", brl(entradas), "cash_in", tone="pos"),
                    kpi_card("Saídas", brl(saidas), "cash_out", tone="neg"),
                ]
            )
            st.write("")
            kpi_row(
                [
                    kpi_card(
                        "Saldo do dia",
                        brl(saldo),
                        "bank",
                        delta="positivo" if saldo >= 0 else "negativo",
                        delta_tone="pos" if saldo >= 0 else "neg",
                        hint=plural(len(do_dia), "lançamento", "lançamentos"),
                        tone="brand",
                    )
                ]
            )

            notice(
                "Vendas e compras entram no caixa automaticamente. "
                "Use esta tela para o que não passa pelo balcão: aluguel, contas, "
                "salários e aportes.",
                "info",
                icon_name="bulb",
            )

    # ------------------------------------------------------------------- extrato
    elif opcao == "extrato":
        section("filter", "Filtros")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2], vertical_alignment="bottom")
        with c1:
            data_inicio = st.date_input(
                "Início", value=date.today().replace(day=1), format="DD/MM/YYYY"
            )
        with c2:
            data_fim = st.date_input("Fim", value=date.today(), format="DD/MM/YYYY")
        with c3:
            f_tipo = st.selectbox("Tipo", ["Todos", "entrada", "saída"], format_func=str.capitalize)
        with c4:
            f_categoria = st.text_input("Categoria", placeholder="Filtrar por texto")

        transacoes = [
            t
            for t in carregar(data_inicio, data_fim)
            if (f_tipo == "Todos" or t.tipo == f_tipo)
            and (not f_categoria or f_categoria.lower() in t.categoria.lower())
        ]

        if not transacoes:
            empty_state(
                "wallet",
                "Nenhum lançamento no período",
                "Ajuste os filtros ou registre um novo lançamento.",
            )
        else:
            entradas = sum(float(t.valor) for t in transacoes if t.tipo == "entrada")
            saidas = sum(float(t.valor) for t in transacoes if t.tipo == "saída")
            saldo = entradas - saidas

            kpi_row(
                [
                    kpi_card("Entradas", brl(entradas), "cash_in", tone="pos"),
                    kpi_card("Saídas", brl(saidas), "cash_out", tone="neg"),
                    kpi_card(
                        "Saldo",
                        brl(saldo),
                        "bank",
                        delta="positivo" if saldo >= 0 else "negativo",
                        delta_tone="pos" if saldo >= 0 else "neg",
                        tone="brand",
                    ),
                    kpi_card("Lançamentos", num(len(transacoes)), "list"),
                ]
            )

            section("list", "Extrato")
            df = pd.DataFrame(
                [
                    {
                        "Nº": t.id,
                        "Data": data_br(t.data),
                        "Tipo": t.tipo.capitalize(),
                        "Descrição": t.descricao,
                        "Categoria": t.categoria,
                        "Valor": brl(t.valor),
                    }
                    for t in transacoes
                ]
            )
            data_table(df, height=400)

            c_export, _ = st.columns([1, 3])
            with c_export:
                download_csv(df, f"extrato_{data_inicio}_{data_fim}.csv", "Exportar extrato")

            section("trash", "Excluir lançamento")
            c1, c2 = st.columns([2, 2], vertical_alignment="bottom")
            with c1:
                alvo = st.selectbox(
                    "Lançamento",
                    options=[t.id for t in transacoes],
                    format_func=lambda tid: next(
                        f"{tid} · {t.descricao} · {brl(t.valor)}"
                        for t in transacoes
                        if t.id == tid
                    ),
                )
            with c2:
                confirmar = st.checkbox(f"Confirmo a exclusão do lançamento {alvo}")

            if st.button(
                "Excluir lançamento",
                disabled=not confirmar,
                icon=material("trash"),
            ):
                transacao = db.query(Transacao).filter(Transacao.id == alvo).first()
                if transacao:
                    db.delete(transacao)
                    db.commit()
                    st.toast("Lançamento excluído.", icon=material("check"))
                    st.rerun()
                else:
                    notice("Lançamento não encontrado.", "error")

    # ------------------------------------------------------------------- análise
    else:
        section("filter", "Período")
        c1, c2 = st.columns(2)
        with c1:
            data_inicio = st.date_input(
                "Início",
                value=date.today().replace(day=1),
                key="fin_ini",
                format="DD/MM/YYYY",
            )
        with c2:
            data_fim = st.date_input(
                "Fim", value=date.today(), key="fin_fim", format="DD/MM/YYYY"
            )

        transacoes = carregar(data_inicio, data_fim)

        if not transacoes:
            empty_state(
                "analytics",
                "Sem dados para analisar",
                "Registre lançamentos no período para ver os gráficos.",
            )
        else:
            df = pd.DataFrame(
                [
                    {
                        "data": t.data,
                        "tipo": t.tipo,
                        "valor": float(t.valor),
                        "categoria": t.categoria,
                    }
                    for t in transacoes
                ]
            )
            entradas = df[df["tipo"] == "entrada"]
            saidas = df[df["tipo"] == "saída"]
            total_entradas = float(entradas["valor"].sum())
            total_saidas = float(saidas["valor"].sum())
            saldo = total_entradas - total_saidas

            kpi_row(
                [
                    kpi_card("Entradas", brl(total_entradas), "cash_in", tone="pos"),
                    kpi_card("Saídas", brl(total_saidas), "cash_out", tone="neg"),
                    kpi_card(
                        "Resultado",
                        brl(saldo),
                        "bank",
                        delta="positivo" if saldo >= 0 else "negativo",
                        delta_tone="pos" if saldo >= 0 else "neg",
                        tone="brand",
                    ),
                    kpi_card(
                        "Ticket médio",
                        brl(df["valor"].mean()),
                        "target",
                        hint=plural(len(df), "lançamento", "lançamentos"),
                    ),
                ]
            )

            section("bar_chart", "Por categoria")
            c1, c2 = st.columns(2, gap="large")
            with c1:
                if entradas.empty:
                    empty_state("cash_in", "Sem entradas no período")
                else:
                    resumo = entradas.groupby("categoria")["valor"].sum().reset_index()
                    st.plotly_chart(
                        charts.hbar(
                            resumo["categoria"], resumo["valor"], "Entradas", charts.POS
                        ),
                        width="stretch",
                    )
            with c2:
                if saidas.empty:
                    empty_state("cash_out", "Sem saídas no período")
                else:
                    resumo = saidas.groupby("categoria")["valor"].sum().reset_index()
                    st.plotly_chart(
                        charts.hbar(
                            resumo["categoria"], resumo["valor"], "Saídas", charts.NEG
                        ),
                        width="stretch",
                    )

            section("line_chart", "Fluxo diário")
            pivot = (
                df.groupby(["data", "tipo"])["valor"]
                .sum()
                .unstack(fill_value=0)
                .reindex(columns=["entrada", "saída"], fill_value=0)
                .sort_index()
            )
            pivot["saldo"] = pivot["entrada"] - pivot["saída"]
            pivot["acumulado"] = pivot["saldo"].cumsum()

            st.plotly_chart(
                charts.cashflow(
                    pivot.index,
                    pivot["entrada"],
                    pivot["saída"],
                    pivot["acumulado"],
                    "Entradas, saídas e saldo acumulado",
                ),
                width="stretch",
            )

finally:
    db.close()
