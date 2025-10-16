import streamlit as st
import pandas as pd
from config.database import SessionLocal
from services.produto_service import ProdutoService
import sys
from pathlib import Path

# Adicionar path
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

# Verificar autenticação
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Por favor, faça login primeiro!")
    st.stop()

# Verificar se user existe e tem os dados necessários
if not st.session_state.user or 'username' not in st.session_state.user:
    st.error("❌ Erro de autenticação. Por favor, faça login novamente.")
    st.stop()

st.set_page_config(page_title="Produtos", page_icon="📦", layout="wide")

st.markdown("# 📦 Gerenciamento de Produtos")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['username']}")
    st.divider()
    
    opcao = st.radio(
        "Selecione uma opção:",
        ["📋 Listar Produtos", "➕ Cadastrar Produto", "✏️ Editar Produto", "📊 Gerenciar Estoque", "🔍 Buscar Produto"],
        label_visibility="collapsed"
    )

db = SessionLocal()

try:
    # LISTAR PRODUTOS
    if opcao == "📋 Listar Produtos":
        st.markdown("## 📋 Lista de Produtos")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            filtro_categoria = st.selectbox(
                "Filtrar por Categoria",
                ["Todas", "bebida", "lanche", "insumo", "sobremesa", "café"],
                key="filtro_cat"
            )
        
        with col2:
            filtro_estoque = st.selectbox(
                "Estoque",
                ["Todos", "Estoque Baixo", "Sem Estoque"],
                key="filtro_est"
            )
        
        with col3:
            apenas_ativos = st.checkbox("Apenas Ativos", value=True)
        
        # Buscar produtos
        produtos = ProdutoService.listar_produtos(db, apenas_ativos=apenas_ativos)
        
        if produtos:
            # Converter para DataFrame
            dados_produtos = []
            for p in produtos:
                # Aplicar filtros
                if filtro_categoria != "Todas" and p.categoria != filtro_categoria:
                    continue
                
                if filtro_estoque == "Estoque Baixo" and p.estoque_atual > p.estoque_minimo:
                    continue
                
                if filtro_estoque == "Sem Estoque" and p.estoque_atual > 0:
                    continue
                
                # Status do estoque
                if p.estoque_atual == 0:
                    status = "❌ Sem estoque"
                elif p.estoque_atual <= p.estoque_minimo:
                    status = "⚠️ Baixo"
                else:
                    status = "✅ OK"
                
                dados_produtos.append({
                    'ID': p.id,
                    'Nome': p.nome,
                    'Categoria': p.categoria,
                    'Preço Venda': f"R$ {float(p.preco_venda):.2f}",
                    'Custo': f"R$ {float(p.custo_unitario):.2f}",
                    'Estoque': f"{p.estoque_atual} {p.unidade}",
                    'Est. Mínimo': f"{p.estoque_minimo} {p.unidade}",
                    'Status': status,
                    'Margem': f"{((float(p.preco_venda) - float(p.custo_unitario)) / float(p.preco_venda) * 100):.1f}%" if float(p.preco_venda) > 0 else "0.0%"
                })
            
            if dados_produtos:
                df = pd.DataFrame(dados_produtos)
                
                st.markdown(f"**Total de produtos:** {len(df)}")
                
                # Exibir tabela com estilo
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=500,
                    hide_index=True
                )
                
                # Botão para exportar
                col1, col2 = st.columns([4, 1])
                with col2:
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Exportar CSV",
                        data=csv,
                        file_name="produtos.csv",
                        mime="text/csv"
                    )
                
                # Estatísticas
                st.divider()
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Produtos", len(df))
                
                with col2:
                    estoque_baixo = sum(1 for p in produtos if p.estoque_atual <= p.estoque_minimo)
                    st.metric("Estoque Baixo", estoque_baixo)
                
                with col3:
                    valor_total = sum(float(p.preco_venda) * p.estoque_atual for p in produtos)
                    st.metric("Valor Estoque", f"R$ {valor_total:,.2f}")
                
                with col4:
                    categorias = len(set(p.categoria for p in produtos))
                    st.metric("Categorias", categorias)
            else:
                st.info("📊 Nenhum produto encontrado com os filtros aplicados.")
        else:
            st.info("📦 Nenhum produto cadastrado ainda.")
    
    # CADASTRAR PRODUTO
    elif opcao == "➕ Cadastrar Produto":
        st.markdown("## ➕ Cadastrar Novo Produto")
        
        with st.form("form_cadastro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Produto*", placeholder="Ex: Café Expresso")
                categoria = st.selectbox(
                    "Categoria*",
                    ["bebida", "lanche", "insumo", "sobremesa", "café", "outro"]
                )
                preco_venda = st.number_input(
                    "Preço de Venda (R$)*",
                    min_value=0.01,
                    value=5.00,
                    step=0.50,
                    format="%.2f"
                )
                custo_unitario = st.number_input(
                    "Custo Unitário (R$)*",
                    min_value=0.00,
                    value=2.00,
                    step=0.50,
                    format="%.2f"
                )
            
            with col2:
                estoque_atual = st.number_input(
                    "Estoque Atual*",
                    min_value=0,
                    value=0,
                    step=1
                )
                estoque_minimo = st.number_input(
                    "Estoque Mínimo*",
                    min_value=0,
                    value=10,
                    step=1
                )
                unidade = st.selectbox(
                    "Unidade*",
                    ["un", "ml", "l", "g", "kg", "cx"]
                )
                ativo = st.checkbox("Produto Ativo", value=True)
            
            submit = st.form_submit_button("💾 Cadastrar Produto", use_container_width=True)
            
            if submit:
                if nome and categoria:
                    try:
                        produto = ProdutoService.criar_produto(
                            db=db,
                            nome=nome,
                            categoria=categoria,
                            preco_venda=preco_venda,
                            custo_unitario=custo_unitario,
                            estoque_atual=estoque_atual,
                            estoque_minimo=estoque_minimo,
                            unidade=unidade,
                            ativo=ativo
                        )
                        
                        st.success(f"✅ Produto '{produto.nome}' cadastrado com sucesso!")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao cadastrar produto: {str(e)}")
                else:
                    st.warning("⚠️ Por favor, preencha todos os campos obrigatórios!")
    
    # EDITAR PRODUTO
    elif opcao == "✏️ Editar Produto":
        st.markdown("## ✏️ Editar Produto")
        
        produtos = ProdutoService.listar_produtos(db, apenas_ativos=False)
        
        if produtos:
            opcoes_produtos = {f"{p.id} - {p.nome}": p.id for p in produtos}
            
            produto_selecionado = st.selectbox(
                "Selecione o Produto",
                options=list(opcoes_produtos.keys())
            )
            
            if produto_selecionado:
                produto_id = opcoes_produtos[produto_selecionado]
                produto = ProdutoService.buscar_por_id(db, produto_id)
                
                if produto:
                    with st.form("form_edicao"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            nome = st.text_input("Nome do Produto", value=produto.nome)
                            categoria = st.selectbox(
                                "Categoria",
                                ["bebida", "lanche", "insumo", "sobremesa", "café", "outro"],
                                index=["bebida", "lanche", "insumo", "sobremesa", "café", "outro"].index(produto.categoria) if produto.categoria in ["bebida", "lanche", "insumo", "sobremesa", "café", "outro"] else 0
                            )
                            preco_venda_valor = float(produto.preco_venda)
                            if preco_venda_valor < 0.01:
                                preco_venda_valor = 0.01
                            
                            preco_venda = st.number_input(
                                "Preço de Venda (R$)",
                                min_value=0.01,
                                value=preco_venda_valor,
                                step=0.50,
                                format="%.2f"
                            )
                            custo_unitario = st.number_input(
                                "Custo Unitário (R$)",
                                min_value=0.00,
                                value=float(produto.custo_unitario),
                                step=0.50,
                                format="%.2f"
                            )
                        
                        with col2:
                            estoque_atual = st.number_input(
                                "Estoque Atual",
                                min_value=0,
                                value=produto.estoque_atual,
                                step=1
                            )
                            estoque_minimo = st.number_input(
                                "Estoque Mínimo",
                                min_value=0,
                                value=produto.estoque_minimo,
                                step=1
                            )
                            unidade = st.selectbox(
                                "Unidade",
                                ["un", "ml", "l", "g", "kg", "cx"],
                                index=["un", "ml", "l", "g", "kg", "cx"].index(produto.unidade) if produto.unidade in ["un", "ml", "l", "g", "kg", "cx"] else 0
                            )
                            ativo = st.checkbox("Produto Ativo", value=produto.ativo)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            atualizar = st.form_submit_button("💾 Atualizar", use_container_width=True)
                        
                        with col2:
                            desativar = st.form_submit_button("🗑️ Desativar", use_container_width=True, type="secondary")
                        
                        if atualizar:
                            try:
                                ProdutoService.atualizar_produto(
                                    db=db,
                                    id=produto_id,
                                    nome=nome,
                                    categoria=categoria,
                                    preco_venda=preco_venda,
                                    custo_unitario=custo_unitario,
                                    estoque_atual=estoque_atual,
                                    estoque_minimo=estoque_minimo,
                                    unidade=unidade,
                                    ativo=ativo
                                )
                                st.success("✅ Produto atualizado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao atualizar produto: {str(e)}")
                        
                        if desativar:
                            ProdutoService.deletar_produto(db, produto_id)
                            st.success("✅ Produto desativado com sucesso!")
                            st.rerun()
        else:
            st.info("📦 Nenhum produto cadastrado ainda.")
    
    # GERENCIAR ESTOQUE
    elif opcao == "📊 Gerenciar Estoque":
        st.markdown("## 📊 Gerenciamento de Estoque")
        st.markdown("Atualize o estoque de múltiplos produtos simultaneamente")
        
        # Buscar produtos ativos
        produtos = ProdutoService.listar_produtos(db, apenas_ativos=True)
        
        if produtos:
            # Criar DataFrame para edição
            dados_estoque = []
            for p in produtos:
                dados_estoque.append({
                    'ID': p.id,
                    'Produto': p.nome,
                    'Categoria': p.categoria,
                    'Estoque Atual': p.estoque_atual,
                    'Estoque Mínimo': p.estoque_minimo,
                    'Unidade': p.unidade,
                    'Custo Unitário': float(p.custo_unitario),
                    'Status': '❌ Sem estoque' if p.estoque_atual == 0 else '⚠️ Baixo' if p.estoque_atual <= p.estoque_minimo else '✅ OK'
                })
            
            df_estoque = pd.DataFrame(dados_estoque)
            
            # Exibir tabela editável
            st.markdown("### 📋 Tabela de Estoque (Editável)")
            st.info("💡 **Dica:** Clique nas células de 'Estoque Atual' para editar os valores diretamente na tabela.")
            
            # Criar editor de dados
            edited_df = st.data_editor(
                df_estoque[['Produto', 'Categoria', 'Estoque Atual', 'Estoque Mínimo', 'Unidade', 'Custo Unitário', 'Status']],
                use_container_width=True,
                height=500,
                hide_index=True,
                column_config={
                    'Produto': st.column_config.TextColumn("Produto", width="medium"),
                    'Categoria': st.column_config.TextColumn("Categoria", width="small"),
                    'Estoque Atual': st.column_config.NumberColumn("Estoque Atual", min_value=0, step=1),
                    'Estoque Mínimo': st.column_config.NumberColumn("Estoque Mín.", min_value=0, step=1),
                    'Unidade': st.column_config.TextColumn("Unidade", width="small"),
                    'Custo Unitário': st.column_config.NumberColumn("Custo (R$)", format="R$ %.2f"),
                    'Status': st.column_config.TextColumn("Status", width="small")
                },
                disabled=['Produto', 'Categoria', 'Unidade', 'Custo Unitário', 'Status']
            )
            
            # Botão para salvar alterações
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col2:
                if st.button("💾 Salvar Alterações", use_container_width=True, type="primary"):
                    try:
                        alteracoes = 0
                        for index, row in edited_df.iterrows():
                            produto_id = dados_estoque[index]['ID']
                            novo_estoque = int(row['Estoque Atual'])
                            novo_minimo = int(row['Estoque Mínimo'])
                            
                            # Buscar produto
                            produto = ProdutoService.buscar_por_id(db, produto_id)
                            if produto:
                                # Verificar se houve alteração
                                if produto.estoque_atual != novo_estoque or produto.estoque_minimo != novo_minimo:
                                    ProdutoService.atualizar_estoque_e_minimo(
                                        db=db,
                                        id=produto_id,
                                        estoque_atual=novo_estoque,
                                        estoque_minimo=novo_minimo
                                    )
                                    alteracoes += 1
                        
                        if alteracoes > 0:
                            st.success(f"✅ {alteracoes} produto(s) atualizado(s) com sucesso!")
                            st.rerun()
                        else:
                            st.info("ℹ️ Nenhuma alteração foi feita.")
                    
                    except Exception as e:
                        st.error(f"❌ Erro ao atualizar estoque: {str(e)}")
            
            with col3:
                # Botão para resetar estoque
                if st.button("🔄 Resetar", use_container_width=True):
                    st.rerun()
            
            # Estatísticas do estoque
            st.divider()
            st.markdown("### 📊 Estatísticas do Estoque")
            
            col1, col2, col3, col4 = st.columns(4)
            
            total_produtos = len(produtos)
            estoque_baixo = sum(1 for p in produtos if p.estoque_atual <= p.estoque_minimo and p.estoque_atual > 0)
            sem_estoque = sum(1 for p in produtos if p.estoque_atual == 0)
            valor_total = sum(float(p.custo_unitario) * p.estoque_atual for p in produtos)
            
            with col1:
                st.metric("Total Produtos", total_produtos)
            
            with col2:
                st.metric("Estoque Baixo", estoque_baixo, delta_color="inverse")
            
            with col3:
                st.metric("Sem Estoque", sem_estoque, delta_color="inverse")
            
            with col4:
                st.metric("Valor Total Estoque", f"R$ {valor_total:,.2f}")
            
            # Alertas
            if estoque_baixo > 0 or sem_estoque > 0:
                st.divider()
                st.markdown("### ⚠️ Alertas de Estoque")
                
                if sem_estoque > 0:
                    st.error(f"❌ **{sem_estoque} produto(s) sem estoque:**")
                    produtos_sem_estoque = [p for p in produtos if p.estoque_atual == 0]
                    for p in produtos_sem_estoque[:5]:
                        st.markdown(f"- **{p.nome}**: {p.estoque_atual} {p.unidade}")
                
                if estoque_baixo > 0:
                    st.warning(f"⚠️ **{estoque_baixo} produto(s) com estoque baixo:**")
                    produtos_baixo = [p for p in produtos if p.estoque_atual <= p.estoque_minimo and p.estoque_atual > 0]
                    for p in produtos_baixo[:5]:
                        st.markdown(f"- **{p.nome}**: {p.estoque_atual} {p.unidade} (mín: {p.estoque_minimo})")
        else:
            st.info("📦 Nenhum produto ativo cadastrado.")
    
    # BUSCAR PRODUTO
    elif opcao == "🔍 Buscar Produto":
        st.markdown("## 🔍 Buscar Produto")
        
        busca = st.text_input("Digite o nome do produto", placeholder="Ex: Café")
        
        if busca:
            produtos = ProdutoService.listar_produtos(db, apenas_ativos=False)
            resultados = [p for p in produtos if busca.lower() in p.nome.lower()]
            
            if resultados:
                st.markdown(f"**{len(resultados)} produto(s) encontrado(s)**")
                
                for produto in resultados:
                    with st.expander(f"📦 {produto.nome}"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown(f"**ID:** {produto.id}")
                            st.markdown(f"**Categoria:** {produto.categoria}")
                            st.markdown(f"**Status:** {'✅ Ativo' if produto.ativo else '❌ Inativo'}")
                        
                        with col2:
                            st.markdown(f"**Preço Venda:** R$ {float(produto.preco_venda):.2f}")
                            st.markdown(f"**Custo:** R$ {float(produto.custo_unitario):.2f}")
                            margem = ((float(produto.preco_venda) - float(produto.custo_unitario)) / float(produto.preco_venda) * 100)
                            st.markdown(f"**Margem:** {margem:.1f}%")
                        
                        with col3:
                            st.markdown(f"**Estoque:** {produto.estoque_atual} {produto.unidade}")
                            st.markdown(f"**Estoque Mín.:** {produto.estoque_minimo} {produto.unidade}")
                            
                            if produto.estoque_atual == 0:
                                st.error("❌ Sem estoque")
                            elif produto.estoque_atual <= produto.estoque_minimo:
                                st.warning("⚠️ Estoque baixo")
                            else:
                                st.success("✅ Estoque OK")
            else:
                st.info("📊 Nenhum produto encontrado com esse nome.")

finally:
    db.close()
