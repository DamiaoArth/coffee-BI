import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.page import setup_page  # noqa: E402

user = setup_page(
    title="Compras",
    icon_name="truck",
    heading="Compras e fornecedores",
    subtitle="Entrada de mercadoria, custo médio e histórico por fornecedor.",
)

from config.database import SessionLocal  # noqa: E402
from services.compra_service import CompraService  # noqa: E402
from services.produto_service import ProdutoService  # noqa: E402
from ui.components import (  # noqa: E402
    data_table,
    definition_list,
    download_csv,
    empty_state,
    kpi_card,
    kpi_row,
    line_item,
    notice,
    section,
    sidebar_nav,
    total_line,
)
from ui.format import brl, data_br, num, plural  # noqa: E402
from ui.icons import material  # noqa: E402

METODOS = ["dinheiro", "transferência", "boleto", "cartão crédito", "pix"]

st.session_state.setdefault("itens_compra", [])

with st.sidebar:
    opcao = sidebar_nav(
        [
            ("nova", "Nova compra", "plus"),
            ("historico", "Histórico", "list"),
        ],
        state_key="nav_compras",
    )

db = SessionLocal()

try:
    # ---------------------------------------------------------------- nova compra
    if opcao == "nova":
        col_form, col_itens = st.columns([2, 1], gap="large")

        with col_form:
            section("truck", "Dados da compra")
            c1, c2 = st.columns(2, gap="large")
            with c1:
                fornecedor = st.text_input(
                    "Fornecedor*", placeholder="Ex.: Distribuidora Central"
                )
                data_compra = st.date_input(
                    "Data da compra", value=date.today(), format="DD/MM/YYYY"
                )
            with c2:
                metodo = st.selectbox("Forma de pagamento", METODOS)
                observacoes = st.text_area("Observações", placeholder="Opcional.")

            section("box", "Itens")
            produtos = ProdutoService.listar_produtos(db, apenas_ativos=True)

            if not produtos:
                empty_state(
                    "box",
                    "Nenhum produto ativo",
                    "Cadastre produtos antes de lançar uma compra.",
                )
            else:
                rotulos = {f"{p.nome} ({p.unidade})": p.id for p in produtos}
                c_prod, c_qtd, c_preco, c_btn = st.columns(
                    [3, 1, 1.2, 1], vertical_alignment="bottom"
                )
                with c_prod:
                    escolhido = st.selectbox("Produto", options=list(rotulos.keys()))
                with c_qtd:
                    quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)
                with c_preco:
                    preco = st.number_input(
                        "Custo unitário (R$)",
                        min_value=0.01,
                        value=1.00,
                        step=0.50,
                        format="%.2f",
                    )
                with c_btn:
                    adicionar = st.button(
                        "Adicionar", width="stretch", icon=material("plus")
                    )

                if adicionar:
                    produto = ProdutoService.buscar_por_id(db, rotulos[escolhido])
                    if produto is None:
                        notice("Produto não encontrado.", "error")
                    else:
                        st.session_state.itens_compra.append(
                            {
                                "id_produto": produto.id,
                                "nome": produto.nome,
                                "quantidade": quantidade,
                                "preco_unitario": float(preco),
                                "subtotal": float(preco) * quantidade,
                            }
                        )
                        st.rerun()

        with col_itens:
            section("receipt", "Resumo")

            if not st.session_state.itens_compra:
                empty_state("truck", "Nenhum item", "Adicione produtos à compra.")
            else:
                remover = None
                for idx, item in enumerate(st.session_state.itens_compra):
                    c_info, c_del = st.columns([3.4, 1.6], vertical_alignment="center")
                    with c_info:
                        line_item(
                            item["nome"],
                            f"{item['quantidade']} × {brl(item['preco_unitario'])}",
                            brl(item["subtotal"]),
                        )
                    with c_del:
                        if st.button(
                            "Remover",
                            key=f"del_compra_{idx}",
                            icon=material("trash"),
                            width="stretch",
                        ):
                            remover = idx

                if remover is not None:
                    st.session_state.itens_compra.pop(remover)
                    st.rerun()

                total = sum(item["subtotal"] for item in st.session_state.itens_compra)
                total_line("Total", brl(total))

                c_ok, c_limpar = st.columns(2)
                with c_ok:
                    finalizar = st.button(
                        "Registrar compra",
                        width="stretch",
                        type="primary",
                        icon=material("check"),
                    )
                with c_limpar:
                    limpar = st.button(
                        "Limpar", width="stretch", icon=material("trash")
                    )

                if limpar:
                    st.session_state.itens_compra = []
                    st.rerun()

                if finalizar:
                    if not fornecedor.strip():
                        notice("Informe o fornecedor antes de registrar.", "warning")
                    else:
                        try:
                            compra = CompraService.criar_compra(
                                db=db,
                                data_compra=data_compra,
                                fornecedor=fornecedor.strip(),
                                metodo_pagamento=metodo,
                                itens=st.session_state.itens_compra,
                                observacoes=observacoes or None,
                            )
                            st.session_state.itens_compra = []
                            st.toast(
                                f"Compra {compra.id} registrada e estoque atualizado.",
                                icon=material("check"),
                            )
                            st.rerun()
                        except Exception as erro:
                            notice(f"Não foi possível registrar a compra: {erro}", "error")

    # ----------------------------------------------------------------- histórico
    else:
        section("filter", "Período")
        c1, c2 = st.columns(2)
        with c1:
            data_inicio = st.date_input(
                "Início",
                value=date.today().replace(day=1),
                key="compras_ini",
                format="DD/MM/YYYY",
            )
        with c2:
            data_fim = st.date_input(
                "Fim", value=date.today(), key="compras_fim", format="DD/MM/YYYY"
            )

        compras = CompraService.listar_compras(db, data_inicio, data_fim)

        if not compras:
            empty_state(
                "truck",
                "Nenhuma compra no período",
                "Ajuste as datas ou registre uma nova entrada de mercadoria.",
            )
        else:
            total = sum(float(c.valor_total) for c in compras)
            fornecedores = {c.fornecedor for c in compras}

            kpi_row(
                [
                    kpi_card("Compras", num(len(compras)), "truck", tone="brand"),
                    kpi_card("Total gasto", brl(total), "money", tone="neg"),
                    kpi_card("Média por compra", brl(total / len(compras)), "target"),
                    kpi_card("Fornecedores", num(len(fornecedores)), "storefront"),
                ]
            )

            section("list", "Lançamentos")
            df = pd.DataFrame(
                [
                    {
                        "Nº": c.id,
                        "Data": data_br(c.data),
                        "Fornecedor": c.fornecedor,
                        "Valor": brl(c.valor_total),
                        "Pagamento": c.metodo_pagamento,
                        "Itens": len(c.itens),
                    }
                    for c in compras
                ]
            )
            data_table(df, height=340)

            c_export, _ = st.columns([1, 3])
            with c_export:
                download_csv(df, f"compras_{data_inicio}_{data_fim}.csv", "Exportar período")

            section("search", "Detalhe")
            for compra in compras:
                titulo = (
                    f"Compra {compra.id} · {data_br(compra.data)} · "
                    f"{compra.fornecedor} · {brl(compra.valor_total)}"
                )
                with st.expander(titulo, icon=material("truck")):
                    c1, c2 = st.columns([1, 1.4], gap="large")
                    with c1:
                        definition_list(
                            [
                                ("Fornecedor", compra.fornecedor),
                                ("Data", data_br(compra.data)),
                                ("Pagamento", compra.metodo_pagamento),
                                ("Itens", plural(len(compra.itens), "item", "itens")),
                                ("Total", brl(compra.valor_total)),
                            ]
                        )
                        if compra.observacoes:
                            st.caption(compra.observacoes)
                    with c2:
                        data_table(
                            pd.DataFrame(
                                [
                                    {
                                        "Produto": item.produto.nome,
                                        "Qtd.": item.quantidade,
                                        "Unitário": brl(item.preco_unitario),
                                        "Subtotal": brl(item.subtotal),
                                    }
                                    for item in compra.itens
                                ]
                            )
                        )

finally:
    db.close()
