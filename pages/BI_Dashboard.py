import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.page import setup_page  # noqa: E402

user = setup_page(
    title="BI",
    icon_name="analytics",
    heading="Business Intelligence",
    subtitle="Faturamento, mix de produtos, pagamentos, caixa e margem por período.",
)

from config.database import SessionLocal  # noqa: E402
from services.produto_service import ProdutoService  # noqa: E402
from services.relatorio_service import RelatorioService  # noqa: E402
from ui import charts  # noqa: E402
from ui.components import (  # noqa: E402
    data_table,
    download_csv,
    empty_state,
    kpi_card,
    kpi_row,
    notice,
    section,
)
from ui.format import brl, data_br, num, pct, plural, signed_pct  # noqa: E402
from ui.icons import material  # noqa: E402

PRESETS = {
    "Hoje": 0,
    "Últimos 7 dias": 6,
    "Últimos 30 dias": 29,
    "Últimos 90 dias": 89,
    "Este ano": None,
    "Personalizado": -1,
}

BLOCOS = ["Vendas", "Produtos", "Categorias", "Pagamentos", "Caixa", "Margem"]

hoje = date.today()

with st.sidebar:
    st.markdown('<p class="erp-navlabel">Período</p>', unsafe_allow_html=True)
    preset = st.selectbox("Intervalo", list(PRESETS.keys()), index=2,
                          label_visibility="collapsed")

    if preset == "Personalizado":
        data_inicio = st.date_input(
            "Início", value=hoje - timedelta(days=29), format="DD/MM/YYYY"
        )
        data_fim = st.date_input("Fim", value=hoje, format="DD/MM/YYYY")
    elif preset == "Este ano":
        data_inicio, data_fim = date(hoje.year, 1, 1), hoje
    else:
        data_inicio, data_fim = hoje - timedelta(days=PRESETS[preset]), hoje

    st.caption(f"{data_br(data_inicio)} a {data_br(data_fim)}")

    st.markdown('<p class="erp-navlabel">Blocos exibidos</p>', unsafe_allow_html=True)
    blocos = st.multiselect(
        "Blocos", BLOCOS, default=BLOCOS[:4], label_visibility="collapsed"
    )

db = SessionLocal()

try:
    df_vendas = RelatorioService.vendas_por_periodo(db, data_inicio, data_fim)

    if df_vendas.empty:
        empty_state(
            "analytics",
            "Sem vendas no período",
            "Selecione outro intervalo ou registre vendas para gerar os indicadores.",
        )
        st.stop()

    dias = (data_fim - data_inicio).days + 1
    faturamento = float(df_vendas["Total"].sum())
    qtd_vendas = int(df_vendas["Quantidade"].sum())
    ticket = faturamento / qtd_vendas if qtd_vendas else 0.0

    anterior = RelatorioService.vendas_por_periodo(
        db, data_inicio - timedelta(days=dias), data_inicio - timedelta(days=1)
    )
    total_anterior = float(anterior["Total"].sum()) if not anterior.empty else 0.0
    variacao = (
        (faturamento - total_anterior) / total_anterior * 100 if total_anterior > 0 else None
    )
    produtos_baixo = ProdutoService.produtos_estoque_baixo(db)

    kpi_row(
        [
            kpi_card(
                "Faturamento",
                brl(faturamento),
                "money",
                delta=signed_pct(variacao) if variacao is not None else "sem base",
                delta_tone=("pos" if variacao >= 0 else "neg") if variacao is not None else "neutral",
                hint="vs. período anterior",
                tone="brand",
            ),
            kpi_card(
                "Vendas",
                num(qtd_vendas),
                "receipt",
                hint=f"em {plural(dias, 'dia', 'dias')}",
                tone="pos",
            ),
            kpi_card("Ticket médio", brl(ticket), "target"),
            kpi_card(
                "Estoque em alerta",
                num(len(produtos_baixo)),
                "alert",
                delta="repor" if produtos_baixo else "tudo certo",
                delta_tone="neg" if produtos_baixo else "pos",
                tone="neg" if produtos_baixo else "neutral",
            ),
        ]
    )

    # ------------------------------------------------------------------- vendas
    if "Vendas" in blocos:
        section("line_chart", "Evolução das vendas")
        c_graf, c_stats = st.columns([2.2, 1], gap="large")
        with c_graf:
            st.plotly_chart(
                charts.area_line(
                    df_vendas["Data"], df_vendas["Total"], "Faturamento", "Faturamento diário"
                ),
                width="stretch",
            )
        with c_stats:
            melhor = df_vendas.loc[df_vendas["Total"].idxmax()]
            kpi_row([kpi_card("Melhor dia", brl(melhor["Total"]), "trophy",
                              hint=data_br(melhor["Data"]), tone="pos")])
            st.write("")
            kpi_row([kpi_card("Média diária", brl(df_vendas["Total"].mean()), "bar_chart")])
            st.write("")
            kpi_row([kpi_card("Menor dia", brl(df_vendas["Total"].min()), "trending_down")])

    # ----------------------------------------------------------------- produtos
    df_produtos = None
    if "Produtos" in blocos:
        section("trophy", "Produtos mais vendidos")
        df_produtos = RelatorioService.produtos_mais_vendidos(db, data_inicio, data_fim, top=10)

        if df_produtos.empty:
            empty_state("box", "Sem itens vendidos no período")
        else:
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.plotly_chart(
                    charts.hbar(
                        df_produtos["Produto"], df_produtos["Quantidade"], "Volume vendido"
                    ),
                    width="stretch",
                )
            with c2:
                top5 = df_produtos.head(5)
                st.plotly_chart(
                    charts.donut(
                        top5["Produto"], top5["Total"], "Top 5 no faturamento"
                    ),
                    width="stretch",
                )

            with st.expander("Ver tabela", icon=material("list")):
                data_table(
                    df_produtos.assign(
                        Total=df_produtos["Total"].map(brl),
                        Quantidade=df_produtos["Quantidade"].map(num),
                    )
                )

    # --------------------------------------------------------------- categorias
    if "Categorias" in blocos:
        section("layers", "Desempenho por categoria")
        df_categorias = RelatorioService.vendas_por_categoria(db, data_inicio, data_fim)

        if df_categorias.empty:
            empty_state("layers", "Sem dados por categoria")
        else:
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.plotly_chart(
                    charts.donut(
                        df_categorias["Categoria"],
                        df_categorias["Total"],
                        "Faturamento por categoria",
                    ),
                    width="stretch",
                )
            with c2:
                st.plotly_chart(
                    charts.vbar(
                        df_categorias["Categoria"],
                        df_categorias["Quantidade"],
                        "Volume por categoria",
                    ),
                    width="stretch",
                )

            lider = df_categorias.loc[df_categorias["Total"].idxmax()]
            notice(
                f"Categoria líder: <strong>{lider['Categoria']}</strong>, "
                f"com {brl(lider['Total'])} no período.",
                "success",
                icon_name="trophy",
            )

    # --------------------------------------------------------------- pagamentos
    if "Pagamentos" in blocos:
        section("card", "Formas de pagamento")
        df_pag = RelatorioService.vendas_por_metodo_pagamento(db, data_inicio, data_fim)

        if df_pag.empty:
            empty_state("card", "Sem dados de pagamento")
        else:
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.plotly_chart(
                    charts.hbar(df_pag["Método"], df_pag["Total"], "Faturamento por método"),
                    width="stretch",
                )
            with c2:
                st.plotly_chart(
                    charts.donut(
                        df_pag["Método"], df_pag["Quantidade"], "Transações por método"
                    ),
                    width="stretch",
                )

    # -------------------------------------------------------------------- caixa
    if "Caixa" in blocos:
        section("wallet", "Fluxo de caixa")
        df_fluxo = RelatorioService.fluxo_caixa(db, data_inicio, data_fim)

        if df_fluxo.empty:
            empty_state("wallet", "Sem movimentação de caixa no período")
        else:
            entradas = float(df_fluxo["entrada"].sum())
            saidas = float(df_fluxo["saida"].sum())
            saldo = entradas - saidas
            acumulado = float(df_fluxo["saldo_acumulado"].iloc[-1])

            kpi_row(
                [
                    kpi_card("Entradas", brl(entradas), "cash_in", tone="pos"),
                    kpi_card("Saídas", brl(saidas), "cash_out", tone="neg"),
                    kpi_card(
                        "Resultado",
                        brl(saldo),
                        "bank",
                        delta="positivo" if saldo >= 0 else "negativo",
                        delta_tone="pos" if saldo >= 0 else "neg",
                        tone="brand",
                    ),
                    kpi_card("Saldo acumulado", brl(acumulado), "wallet"),
                ]
            )
            st.plotly_chart(
                charts.cashflow(
                    df_fluxo["data"],
                    df_fluxo["entrada"],
                    df_fluxo["saida"],
                    df_fluxo["saldo_acumulado"],
                    "Entradas, saídas e saldo acumulado",
                ),
                width="stretch",
            )

    # ------------------------------------------------------------------- margem
    df_lucro = None
    if "Margem" in blocos:
        section("percent", "Margem por produto")
        df_lucro = RelatorioService.lucro_por_produto(db, data_inicio, data_fim)

        if df_lucro.empty:
            empty_state("percent", "Sem dados de margem no período")
        else:
            top_lucro = df_lucro.nlargest(10, "Lucro")
            lucro_total = float(df_lucro["Lucro"].sum())
            receita_total = float(df_lucro["Receita"].sum())
            margem_geral = lucro_total / receita_total * 100 if receita_total else 0.0
            campeao = df_lucro.loc[df_lucro["Lucro"].idxmax()]

            kpi_row(
                [
                    kpi_card("Lucro bruto", brl(lucro_total), "money", tone="pos"),
                    kpi_card("Margem geral", pct(margem_geral), "percent", tone="brand"),
                    kpi_card(
                        "Produto mais lucrativo",
                        str(campeao["Produto"]),
                        "trophy",
                        hint=brl(campeao["Lucro"]),
                    ),
                ]
            )

            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.plotly_chart(
                    charts.hbar(
                        top_lucro["Produto"], top_lucro["Lucro"], "Lucro por produto", charts.POS
                    ),
                    width="stretch",
                )
            with c2:
                st.plotly_chart(
                    charts.hbar(
                        top_lucro["Produto"],
                        top_lucro["Margem %"],
                        "Margem por produto (%)",
                        charts.BRAND,
                    ),
                    width="stretch",
                )

            with st.expander("Ver tabela completa", icon=material("list")):
                data_table(
                    df_lucro.assign(
                        Receita=df_lucro["Receita"].map(brl),
                        Custo=df_lucro["Custo"].map(brl),
                        Lucro=df_lucro["Lucro"].map(brl),
                        **{"Margem %": df_lucro["Margem %"].map(pct)},
                    )
                )

    # ---------------------------------------------------------------- destaques
    section("bulb", "Destaques", "Leituras automáticas a partir dos dados do período.")
    c1, c2 = st.columns(2, gap="large")

    with c1:
        if df_lucro is not None and not df_lucro.empty:
            oportunidades = df_lucro[
                (df_lucro["Margem %"] > 50)
                & (df_lucro["Quantidade"] < df_lucro["Quantidade"].median())
            ].head(3)
            if oportunidades.empty:
                notice("Nenhum produto com margem alta e giro baixo neste período.", "info")
            else:
                itens = "".join(
                    f"<li><strong>{linha['Produto']}</strong> — margem "
                    f"{pct(linha['Margem %'])}, giro abaixo da mediana</li>"
                    for _, linha in oportunidades.iterrows()
                )
                notice(
                    "Margem alta e giro baixo. Vale destacar no balcão ou em combo:"
                    f"<ul style='margin:6px 0 0 18px;padding:0'>{itens}</ul>",
                    "success",
                    icon_name="trending_up",
                )
        else:
            notice("Ative o bloco Margem para ver oportunidades de mix.", "info")

    with c2:
        if produtos_baixo:
            itens = "".join(
                f"<li><strong>{p.nome}</strong> — {p.estoque_atual} {p.unidade} "
                f"(mínimo {p.estoque_minimo})</li>"
                for p in produtos_baixo[:5]
            )
            notice(
                f"{plural(len(produtos_baixo), 'produto precisa', 'produtos precisam')} "
                "de reposição:"
                f"<ul style='margin:6px 0 0 18px;padding:0'>{itens}</ul>",
                "warning",
            )
        else:
            notice("Estoque dentro do mínimo em todos os produtos.", "success")

    # ---------------------------------------------------------------- exportação
    section("download", "Exportar")
    c1, c2, c3 = st.columns(3)
    with c1:
        download_csv(
            df_vendas, f"vendas_{data_inicio}_{data_fim}.csv", "Vendas", key="exp_vendas"
        )
    with c2:
        if df_produtos is not None and not df_produtos.empty:
            download_csv(
                df_produtos,
                f"produtos_{data_inicio}_{data_fim}.csv",
                "Produtos",
                key="exp_produtos",
            )
    with c3:
        if df_lucro is not None and not df_lucro.empty:
            download_csv(
                df_lucro, f"margem_{data_inicio}_{data_fim}.csv", "Margem", key="exp_margem"
            )

finally:
    db.close()
