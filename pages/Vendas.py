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
    title="Vendas",
    icon_name="cart",
    heading="Vendas",
    subtitle="Registro de vendas, histórico e consulta por número.",
)

from config.database import SessionLocal  # noqa: E402
from services.produto_service import ProdutoService  # noqa: E402
from services.venda_service import VendaService  # noqa: E402
from ui.components import (  # noqa: E402
    badge,
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
from ui.format import brl, data_br, hora_br, num, plural  # noqa: E402
from ui.icons import material  # noqa: E402
from ui.page import ROLES_GESTAO  # noqa: E402

st.session_state.setdefault("carrinho", [])

with st.sidebar:
    opcao = sidebar_nav(
        [
            ("nova", "Nova venda", "plus"),
            ("historico", "Histórico", "list"),
            ("consulta", "Consultar venda", "search"),
        ],
        state_key="nav_vendas",
    )

db = SessionLocal()

try:
    # ---------------------------------------------------------------- nova venda
    if opcao == "nova":
        col_form, col_carrinho = st.columns([2, 1], gap="large")

        with col_form:
            section("box", "Adicionar produtos")

            produtos = [
                p
                for p in ProdutoService.listar_produtos(db, apenas_ativos=True)
                if p.estoque_atual > 0
            ]

            if not produtos:
                empty_state(
                    "box",
                    "Nenhum produto disponível",
                    "Todos os itens estão sem estoque. Registre uma compra para repor.",
                )
            else:
                rotulos = {
                    f"{p.nome} · {brl(p.preco_venda)} · {p.estoque_atual} {p.unidade}": p.id
                    for p in produtos
                }

                c_prod, c_qtd, c_btn = st.columns([3, 1, 1], vertical_alignment="bottom")
                with c_prod:
                    escolhido = st.selectbox(
                        "Produto", options=list(rotulos.keys()), key="venda_produto"
                    )
                with c_qtd:
                    quantidade = st.number_input(
                        "Quantidade", min_value=1, value=1, step=1, key="venda_qtd"
                    )
                with c_btn:
                    adicionar = st.button(
                        "Adicionar",
                        width="stretch",
                        icon=material("plus"),
                    )

                if adicionar:
                    produto = ProdutoService.buscar_por_id(db, rotulos[escolhido])
                    if produto is None:
                        notice("Produto não encontrado.", "error")
                    else:
                        no_carrinho = next(
                            (
                                item
                                for item in st.session_state.carrinho
                                if item["id_produto"] == produto.id
                            ),
                            None,
                        )
                        atual = no_carrinho["quantidade"] if no_carrinho else 0
                        if atual + quantidade > produto.estoque_atual:
                            notice(
                                f"Estoque insuficiente. Disponível: "
                                f"{produto.estoque_atual} {produto.unidade}.",
                                "warning",
                            )
                        elif no_carrinho:
                            no_carrinho["quantidade"] = atual + quantidade
                            no_carrinho["subtotal"] = float(produto.preco_venda) * (
                                atual + quantidade
                            )
                            st.rerun()
                        else:
                            st.session_state.carrinho.append(
                                {
                                    "id_produto": produto.id,
                                    "nome": produto.nome,
                                    "quantidade": quantidade,
                                    "preco_unitario": float(produto.preco_venda),
                                    "subtotal": float(produto.preco_venda) * quantidade,
                                }
                            )
                            st.rerun()

                section("list", "Catálogo disponível")
                data_table(
                    pd.DataFrame(
                        [
                            {
                                "Produto": p.nome,
                                "Categoria": p.categoria,
                                "Preço": brl(p.preco_venda),
                                "Estoque": f"{p.estoque_atual} {p.unidade}",
                            }
                            for p in produtos
                        ]
                    ),
                    height=320,
                )

        with col_carrinho:
            section("receipt", "Carrinho")

            if not st.session_state.carrinho:
                empty_state("cart", "Carrinho vazio", "Adicione produtos para iniciar a venda.")
            else:
                remover = None
                for idx, item in enumerate(st.session_state.carrinho):
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
                            key=f"del_item_{idx}",
                            icon=material("trash"),
                            width="stretch",
                        ):
                            remover = idx

                if remover is not None:
                    st.session_state.carrinho.pop(remover)
                    st.rerun()

                total = sum(item["subtotal"] for item in st.session_state.carrinho)
                total_line("Total", brl(total))

                metodo = st.selectbox(
                    "Forma de pagamento",
                    ["dinheiro", "cartão débito", "cartão crédito", "pix", "vale"],
                )
                observacoes = st.text_area(
                    "Observações", placeholder="Opcional. Ex.: sem açúcar."
                )

                c_ok, c_limpar = st.columns(2)
                with c_ok:
                    finalizar = st.button(
                        "Finalizar venda",
                        width="stretch",
                        type="primary",
                        icon=material("check"),
                    )
                with c_limpar:
                    limpar = st.button(
                        "Limpar", width="stretch", icon=material("trash")
                    )

                if limpar:
                    st.session_state.carrinho = []
                    st.rerun()

                if finalizar:
                    try:
                        venda = VendaService.criar_venda(
                            db=db,
                            data_venda=date.today(),
                            metodo_pagamento=metodo,
                            itens=st.session_state.carrinho,
                            observacoes=observacoes or None,
                            funcionario_id=user.get("funcionario_id"),
                        )
                        st.session_state.carrinho = []
                        st.toast(f"Venda {venda.id} registrada.", icon=material("check"))
                        st.rerun()
                    except Exception as erro:
                        notice(f"Não foi possível registrar a venda: {erro}", "error")

    # ----------------------------------------------------------------- histórico
    elif opcao == "historico":
        section("filter", "Período")
        c1, c2 = st.columns(2)
        with c1:
            data_inicio = st.date_input(
                "Início", value=date.today().replace(day=1), key="vendas_ini", format="DD/MM/YYYY"
            )
        with c2:
            data_fim = st.date_input(
                "Fim", value=date.today(), key="vendas_fim", format="DD/MM/YYYY"
            )

        vendas = VendaService.listar_vendas(db, data_inicio, data_fim)

        if not vendas:
            empty_state(
                "receipt",
                "Nenhuma venda no período",
                "Ajuste as datas ou registre uma venda para ver os resultados aqui.",
            )
        else:
            total = sum(float(v.valor_total) for v in vendas)
            ticket = total / len(vendas)
            de_hoje = [v for v in vendas if v.data == date.today()]

            kpi_row(
                [
                    kpi_card("Vendas", num(len(vendas)), "receipt", tone="brand"),
                    kpi_card("Faturamento", brl(total), "money", tone="pos"),
                    kpi_card("Ticket médio", brl(ticket), "target"),
                    kpi_card("Hoje", num(len(de_hoje)), "clock", hint=data_br(date.today())),
                ]
            )

            section("list", "Lançamentos")
            df = pd.DataFrame(
                [
                    {
                        "Nº": v.id,
                        "Data": data_br(v.data),
                        "Hora": hora_br(v.hora),
                        "Valor": brl(v.valor_total),
                        "Pagamento": v.metodo_pagamento,
                        "Itens": len(v.itens) if v.itens else 0,
                    }
                    for v in vendas
                ]
            )
            data_table(df, height=380)

            c_export, _ = st.columns([1, 3])
            with c_export:
                download_csv(df, f"vendas_{data_inicio}_{data_fim}.csv", "Exportar período")

            section("search", "Detalhe da venda")
            escolhida = st.selectbox(
                "Selecione uma venda",
                options=[v.id for v in vendas],
                format_func=lambda vid: f"Venda {vid}",
                key="detalhe_venda",
            )

            venda = VendaService.buscar_por_id(db, escolhida)
            if venda:
                c1, c2 = st.columns([1, 1.4], gap="large")
                with c1:
                    definition_list(
                        [
                            ("Número", str(venda.id)),
                            ("Data", data_br(venda.data)),
                            ("Hora", hora_br(venda.hora)),
                            ("Pagamento", venda.metodo_pagamento),
                            ("Vendedor", venda.funcionario.nome if venda.funcionario else "—"),
                            ("Total", brl(venda.valor_total)),
                        ]
                    )
                    if venda.observacoes:
                        st.caption(venda.observacoes)
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
                                for item in venda.itens
                            ]
                        )
                    )

                if user["nivel_acesso"] in ROLES_GESTAO:
                    st.divider()
                    confirmar = st.checkbox(
                        f"Confirmo o cancelamento da venda {venda.id} e a devolução ao estoque",
                        key=f"conf_cancel_{venda.id}",
                    )
                    if st.button(
                        "Cancelar venda",
                        disabled=not confirmar,
                        icon=material("x_circle"),
                        key=f"cancel_{venda.id}",
                    ):
                        if VendaService.cancelar_venda(db, venda.id):
                            st.toast(f"Venda {venda.id} cancelada.", icon=material("check"))
                            st.rerun()
                        else:
                            notice("Não foi possível cancelar a venda.", "error")

    # ------------------------------------------------------------------ consulta
    else:
        section("search", "Consultar por número")
        c1, c2 = st.columns([1, 3], vertical_alignment="bottom")
        with c1:
            venda_id = st.number_input("Número da venda", min_value=1, value=1, step=1)
        with c2:
            buscar = st.button("Buscar", icon=material("search"))

        if buscar:
            venda = VendaService.buscar_por_id(db, int(venda_id))
            if venda is None:
                empty_state(
                    "search",
                    f"Venda {int(venda_id)} não encontrada",
                    "Confira o número no histórico de vendas.",
                )
            else:
                st.markdown(
                    badge(f"Venda {venda.id}", "brand", "receipt")
                    + " "
                    + badge(venda.metodo_pagamento, "neutral", "card"),
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns([1, 1.4], gap="large")
                with c1:
                    definition_list(
                        [
                            ("Data", data_br(venda.data)),
                            ("Hora", hora_br(venda.hora)),
                            ("Itens", plural(len(venda.itens), "item", "itens")),
                            ("Vendedor", venda.funcionario.nome if venda.funcionario else "—"),
                            ("Total", brl(venda.valor_total)),
                        ]
                    )
                    if venda.observacoes:
                        st.caption(venda.observacoes)
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
                                for item in venda.itens
                            ]
                        )
                    )

finally:
    db.close()
