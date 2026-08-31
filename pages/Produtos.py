import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.page import setup_page  # noqa: E402

user = setup_page(
    title="Produtos",
    icon_name="box",
    heading="Produtos e estoque",
    subtitle="Catálogo, custos, margem e níveis de reposição.",
)

from config.database import SessionLocal  # noqa: E402
from services.produto_service import ProdutoService  # noqa: E402
from ui.components import (  # noqa: E402
    badge,
    data_table,
    definition_list,
    download_csv,
    empty_state,
    kpi_card,
    kpi_row,
    notice,
    section,
    sidebar_nav,
)
from ui.format import brl, num, pct, plural  # noqa: E402
from ui.icons import material  # noqa: E402

CATEGORIAS = ["bebida", "lanche", "insumo", "sobremesa", "café", "outro"]
UNIDADES = ["un", "ml", "l", "g", "kg", "cx"]


def status_estoque(produto):
    if produto.estoque_atual == 0:
        return "Sem estoque", "neg"
    if produto.estoque_atual <= produto.estoque_minimo:
        return "Abaixo do mínimo", "warn"
    return "Normal", "pos"


def margem(produto) -> float:
    preco = float(produto.preco_venda)
    if preco <= 0:
        return 0.0
    return (preco - float(produto.custo_unitario)) / preco * 100


with st.sidebar:
    opcao = sidebar_nav(
        [
            ("catalogo", "Catálogo", "list"),
            ("novo", "Cadastrar", "plus"),
            ("editar", "Editar", "edit"),
            ("estoque", "Estoque", "layers"),
            ("buscar", "Buscar", "search"),
        ],
        state_key="nav_produtos",
    )

db = SessionLocal()

try:
    # ------------------------------------------------------------------ catálogo
    if opcao == "catalogo":
        section("filter", "Filtros")
        c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="bottom")
        with c1:
            f_categoria = st.selectbox("Categoria", ["Todas"] + CATEGORIAS)
        with c2:
            f_estoque = st.selectbox("Estoque", ["Todos", "Abaixo do mínimo", "Sem estoque"])
        with c3:
            apenas_ativos = st.checkbox("Somente ativos", value=True)

        produtos = ProdutoService.listar_produtos(db, apenas_ativos=apenas_ativos)

        filtrados = []
        for p in produtos:
            if f_categoria != "Todas" and p.categoria != f_categoria:
                continue
            if f_estoque == "Abaixo do mínimo" and p.estoque_atual > p.estoque_minimo:
                continue
            if f_estoque == "Sem estoque" and p.estoque_atual > 0:
                continue
            filtrados.append(p)

        if not produtos:
            empty_state(
                "box",
                "Catálogo vazio",
                "Cadastre o primeiro produto para começar a vender.",
            )
        elif not filtrados:
            empty_state("filter", "Nenhum produto com esses filtros", "Amplie os critérios.")
        else:
            baixo = sum(1 for p in produtos if p.estoque_atual <= p.estoque_minimo)
            valor_estoque = sum(float(p.preco_venda) * p.estoque_atual for p in produtos)

            kpi_row(
                [
                    kpi_card("Produtos", num(len(filtrados)), "box", tone="brand",
                             hint=f"de {len(produtos)} no total"),
                    kpi_card("Em alerta", num(baixo), "alert",
                             tone="neg" if baixo else "neutral"),
                    kpi_card("Valor do estoque", brl(valor_estoque), "money", tone="pos",
                             hint="a preço de venda"),
                    kpi_card(
                        "Categorias", num(len({p.categoria for p in produtos})), "layers"
                    ),
                ]
            )

            section("list", "Catálogo")
            df = pd.DataFrame(
                [
                    {
                        "Nº": p.id,
                        "Produto": p.nome,
                        "Categoria": p.categoria,
                        "Preço": brl(p.preco_venda),
                        "Custo": brl(p.custo_unitario),
                        "Margem": pct(margem(p)),
                        "Estoque": f"{p.estoque_atual} {p.unidade}",
                        "Mínimo": f"{p.estoque_minimo} {p.unidade}",
                        "Situação": status_estoque(p)[0],
                    }
                    for p in filtrados
                ]
            )
            data_table(df, height=460)

            c_export, _ = st.columns([1, 3])
            with c_export:
                download_csv(df, "produtos.csv", "Exportar catálogo")

    # ----------------------------------------------------------------- cadastrar
    elif opcao == "novo":
        section("plus", "Novo produto", "Campos marcados com asterisco são obrigatórios.")

        with st.form("cadastro_produto", clear_on_submit=True):
            c1, c2 = st.columns(2, gap="large")
            with c1:
                nome = st.text_input("Nome*", placeholder="Ex.: Café expresso")
                categoria = st.selectbox("Categoria*", CATEGORIAS)
                preco_venda = st.number_input(
                    "Preço de venda (R$)*", min_value=0.01, value=5.00, step=0.50, format="%.2f"
                )
                custo = st.number_input(
                    "Custo unitário (R$)*", min_value=0.00, value=2.00, step=0.50, format="%.2f"
                )
            with c2:
                estoque_atual = st.number_input("Estoque inicial*", min_value=0, value=0, step=1)
                estoque_minimo = st.number_input("Estoque mínimo*", min_value=0, value=10, step=1)
                unidade = st.selectbox("Unidade*", UNIDADES)
                ativo = st.checkbox("Disponível para venda", value=True)

            salvar = st.form_submit_button(
                "Cadastrar produto",
                width="stretch",
                type="primary",
                icon=material("save"),
            )

        if salvar:
            if not nome.strip():
                notice("Informe o nome do produto.", "warning")
            elif custo > preco_venda:
                notice(
                    "O custo unitário está acima do preço de venda. "
                    "Revise os valores antes de salvar.",
                    "warning",
                )
            else:
                try:
                    produto = ProdutoService.criar_produto(
                        db=db,
                        nome=nome.strip(),
                        categoria=categoria,
                        preco_venda=preco_venda,
                        custo_unitario=custo,
                        estoque_atual=estoque_atual,
                        estoque_minimo=estoque_minimo,
                        unidade=unidade,
                        ativo=ativo,
                    )
                    st.toast(f"{produto.nome} cadastrado.", icon=material("check"))
                except Exception as erro:
                    notice(f"Não foi possível cadastrar: {erro}", "error")

    # -------------------------------------------------------------------- editar
    elif opcao == "editar":
        produtos = ProdutoService.listar_produtos(db, apenas_ativos=False)

        if not produtos:
            empty_state("box", "Nada para editar", "Cadastre um produto primeiro.")
        else:
            section("edit", "Editar produto")
            mapa = {f"{p.id} · {p.nome}": p.id for p in produtos}
            escolhido = st.selectbox("Produto", options=list(mapa.keys()))
            produto = ProdutoService.buscar_por_id(db, mapa[escolhido])

            if produto:
                situacao, tom = status_estoque(produto)
                st.markdown(
                    badge(situacao, tom, "box")
                    + " "
                    + badge("Ativo" if produto.ativo else "Inativo",
                            "pos" if produto.ativo else "neutral", "check"),
                    unsafe_allow_html=True,
                )

                with st.form("edicao_produto"):
                    c1, c2 = st.columns(2, gap="large")
                    with c1:
                        nome = st.text_input("Nome", value=produto.nome)
                        categoria = st.selectbox(
                            "Categoria",
                            CATEGORIAS,
                            index=CATEGORIAS.index(produto.categoria)
                            if produto.categoria in CATEGORIAS
                            else 0,
                        )
                        preco_venda = st.number_input(
                            "Preço de venda (R$)",
                            min_value=0.01,
                            value=max(float(produto.preco_venda), 0.01),
                            step=0.50,
                            format="%.2f",
                        )
                        custo = st.number_input(
                            "Custo unitário (R$)",
                            min_value=0.00,
                            value=float(produto.custo_unitario),
                            step=0.50,
                            format="%.2f",
                        )
                    with c2:
                        estoque_atual = st.number_input(
                            "Estoque atual", min_value=0, value=produto.estoque_atual, step=1
                        )
                        estoque_minimo = st.number_input(
                            "Estoque mínimo", min_value=0, value=produto.estoque_minimo, step=1
                        )
                        unidade = st.selectbox(
                            "Unidade",
                            UNIDADES,
                            index=UNIDADES.index(produto.unidade)
                            if produto.unidade in UNIDADES
                            else 0,
                        )
                        ativo = st.checkbox("Disponível para venda", value=produto.ativo)

                    c_ok, c_off = st.columns(2)
                    with c_ok:
                        atualizar = st.form_submit_button(
                            "Salvar alterações",
                            width="stretch",
                            type="primary",
                            icon=material("save"),
                        )
                    with c_off:
                        desativar = st.form_submit_button(
                            "Desativar produto",
                            width="stretch",
                            icon=material("x_circle"),
                        )

                if atualizar:
                    try:
                        ProdutoService.atualizar_produto(
                            db=db,
                            id=produto.id,
                            nome=nome.strip(),
                            categoria=categoria,
                            preco_venda=preco_venda,
                            custo_unitario=custo,
                            estoque_atual=estoque_atual,
                            estoque_minimo=estoque_minimo,
                            unidade=unidade,
                            ativo=ativo,
                        )
                        st.toast("Alterações salvas.", icon=material("check"))
                        st.rerun()
                    except Exception as erro:
                        notice(f"Não foi possível salvar: {erro}", "error")

                if desativar:
                    ProdutoService.deletar_produto(db, produto.id)
                    st.toast(f"{produto.nome} desativado.", icon=material("check"))
                    st.rerun()

    # ------------------------------------------------------------------- estoque
    elif opcao == "estoque":
        produtos = ProdutoService.listar_produtos(db, apenas_ativos=True)

        if not produtos:
            empty_state("layers", "Sem produtos ativos", "Cadastre ou reative um produto.")
        else:
            sem_estoque = [p for p in produtos if p.estoque_atual == 0]
            baixo = [
                p for p in produtos if 0 < p.estoque_atual <= p.estoque_minimo
            ]
            valor_custo = sum(float(p.custo_unitario) * p.estoque_atual for p in produtos)

            kpi_row(
                [
                    kpi_card("Produtos ativos", num(len(produtos)), "box", tone="brand"),
                    kpi_card("Abaixo do mínimo", num(len(baixo)), "alert",
                             tone="warn" if baixo else "neutral"),
                    kpi_card("Sem estoque", num(len(sem_estoque)), "x_circle",
                             tone="neg" if sem_estoque else "neutral"),
                    kpi_card("Valor a custo", brl(valor_custo), "money", tone="pos"),
                ]
            )

            section(
                "layers",
                "Ajuste em lote",
                "Edite as colunas de estoque direto na tabela e salve as alterações.",
            )

            base = pd.DataFrame(
                [
                    {
                        "id": p.id,
                        "Produto": p.nome,
                        "Categoria": p.categoria,
                        "Estoque atual": p.estoque_atual,
                        "Estoque mínimo": p.estoque_minimo,
                        "Unidade": p.unidade,
                        "Custo": float(p.custo_unitario),
                        "Situação": status_estoque(p)[0],
                    }
                    for p in produtos
                ]
            )

            editado = st.data_editor(
                base.drop(columns=["id"]),
                width="stretch",
                height=460,
                hide_index=True,
                key="editor_estoque",
                column_config={
                    "Produto": st.column_config.TextColumn(width="medium"),
                    "Categoria": st.column_config.TextColumn(width="small"),
                    "Estoque atual": st.column_config.NumberColumn(min_value=0, step=1),
                    "Estoque mínimo": st.column_config.NumberColumn(min_value=0, step=1),
                    "Unidade": st.column_config.TextColumn(width="small"),
                    "Custo": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Situação": st.column_config.TextColumn(width="small"),
                },
                disabled=["Produto", "Categoria", "Unidade", "Custo", "Situação"],
            )

            c_salvar, c_reset, _ = st.columns([1, 1, 2])
            with c_salvar:
                salvar = st.button(
                    "Salvar estoque",
                    width="stretch",
                    type="primary",
                    icon=material("save"),
                )
            with c_reset:
                if st.button("Descartar", width="stretch", icon=material("refresh")):
                    st.rerun()

            if salvar:
                try:
                    alteracoes = 0
                    for pos, linha in editado.iterrows():
                        produto_id = int(base.iloc[pos]["id"])
                        novo_atual = int(linha["Estoque atual"])
                        novo_minimo = int(linha["Estoque mínimo"])
                        produto = ProdutoService.buscar_por_id(db, produto_id)
                        if produto and (
                            produto.estoque_atual != novo_atual
                            or produto.estoque_minimo != novo_minimo
                        ):
                            ProdutoService.atualizar_estoque_e_minimo(
                                db=db,
                                id=produto_id,
                                estoque_atual=novo_atual,
                                estoque_minimo=novo_minimo,
                            )
                            alteracoes += 1

                    if alteracoes:
                        st.toast(
                            f"{plural(alteracoes, 'produto atualizado', 'produtos atualizados')}.",
                            icon=material("check"),
                        )
                        st.rerun()
                    else:
                        notice("Nenhuma alteração para salvar.", "info")
                except Exception as erro:
                    notice(f"Não foi possível atualizar o estoque: {erro}", "error")

            if sem_estoque or baixo:
                section("alert", "Reposição")
                if sem_estoque:
                    notice(
                        f"<strong>{plural(len(sem_estoque), 'produto zerado', 'produtos zerados')}"
                        ":</strong> "
                        + ", ".join(p.nome for p in sem_estoque[:6])
                        + ("…" if len(sem_estoque) > 6 else ""),
                        "error",
                    )
                if baixo:
                    notice(
                        f"<strong>{plural(len(baixo), 'produto abaixo', 'produtos abaixo')} "
                        "do mínimo:</strong> "
                        + ", ".join(f"{p.nome} ({p.estoque_atual} {p.unidade})" for p in baixo[:6])
                        + ("…" if len(baixo) > 6 else ""),
                        "warning",
                    )

    # -------------------------------------------------------------------- buscar
    else:
        section("search", "Buscar produto")
        termo = st.text_input(
            "Nome do produto", placeholder="Ex.: café", label_visibility="collapsed"
        )

        if not termo:
            empty_state("search", "Digite para buscar", "A busca considera parte do nome.")
        else:
            produtos = ProdutoService.listar_produtos(db, apenas_ativos=False)
            achados = [p for p in produtos if termo.lower() in p.nome.lower()]

            if not achados:
                empty_state("search", f"Nada encontrado para “{termo}”", "Tente outro termo.")
            else:
                st.caption(plural(len(achados), "produto encontrado", "produtos encontrados"))
                for p in achados:
                    situacao, tom = status_estoque(p)
                    with st.expander(p.nome, icon=material("box")):
                        st.markdown(
                            badge(situacao, tom, "layers")
                            + " "
                            + badge(p.categoria, "brand", "tag")
                            + " "
                            + badge("Ativo" if p.ativo else "Inativo",
                                    "pos" if p.ativo else "neutral", "check"),
                            unsafe_allow_html=True,
                        )
                        st.write("")
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            definition_list(
                                [("Nº", str(p.id)), ("Categoria", p.categoria)]
                            )
                        with c2:
                            definition_list(
                                [
                                    ("Preço", brl(p.preco_venda)),
                                    ("Custo", brl(p.custo_unitario)),
                                    ("Margem", pct(margem(p))),
                                ]
                            )
                        with c3:
                            definition_list(
                                [
                                    ("Estoque", f"{p.estoque_atual} {p.unidade}"),
                                    ("Mínimo", f"{p.estoque_minimo} {p.unidade}"),
                                ]
                            )

finally:
    db.close()
