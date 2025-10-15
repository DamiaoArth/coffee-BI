import streamlit as st
import pandas as pd
from config.database import SessionLocal
from services.compra_service import CompraService
from services.produto_service import ProdutoService
from datetime import date
import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Por favor, faça login primeiro!")
    st.stop()

st.set_page_config(page_title="Compras", page_icon="🛒", layout="wide")

st.markdown("# 🛒 Gerenciamento de Compras")
st.markdown("---")

if 'itens_compra' not in st.session_state:
    st.session_state.itens_compra = []

with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['username']}")
    st.divider()
    
    opcao = st.radio(
        "Selecione uma opção:",
        ["➕ Nova Compra", "📋 Histórico de Compras"],
        label_visibility="collapsed"
    )

db = SessionLocal()

try:
    # NOVA COMPRA
    if opcao == "➕ Nova Compra":
        st.markdown("## ➕ Registrar Nova Compra")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📦 Informações da Compra")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                fornecedor = st.text_input(
                    "Fornecedor*",
                    placeholder="Ex: Distribuidora ABC"
                )
                data_compra = st.date_input(
                    "Data da Compra",
                    value=date.today()
                )
            
            with col_b:
                metodo_pagamento = st.selectbox(
                    "Método de Pagamento",
                    ["dinheiro", "transferência", "boleto", "cartão crédito", "pix"]
                )
                observacoes = st.text_area(
                    "Observações",
                    placeholder="Informações adicionais..."
                )
            
            st.markdown("---")
            st.markdown("### Adicionar Itens")
            
            produtos = ProdutoService.listar_produtos(db, apenas_ativos=True)
            
            if produtos:
                col_prod, col_qtd, col_preco, col_btn = st.columns([3, 1, 1, 1])
                
                with col_prod:
                    opcoes_produtos = {f"{p.nome} ({p.unidade})": p.id for p in produtos}
                    produto_selecionado = st.selectbox(
                        "Produto",
                        options=list(opcoes_produtos.keys()),
                        key="select_produto_compra"
                    )
                
                with col_qtd:
                    quantidade = st.number_input(
                        "Quantidade",
                        min_value=1,
                        value=1,
                        step=1,
                        key="qtd_compra"
                    )
                
                with col_preco:
                    preco_unitario = st.number_input(
                        "Preço Unit. (R$)",
                        min_value=0.01,
                        value=1.00,
                        step=0.50,
                        format="%.2f",
                        key="preco_compra"
                    )
                
                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("➕ Adicionar", use_container_width=True):
                        produto_id = opcoes_produtos[produto_selecionado]
                        produto = ProdutoService.buscar_por_id(db, produto_id)
                        
                        if produto:
                            st.session_state.itens_compra.append({
                                'id_produto': produto.id,
                                'nome': produto.nome,
                                'quantidade': quantidade,
                                'preco_unitario': preco_unitario,
                                'subtotal': preco_unitario * quantidade
                            })
                            st.success(f"✅ {produto.nome} adicionado!")
                            st.rerun()
        
        with col2:
            st.markdown("### 📋 Itens da Compra")
            
            if st.session_state.itens_compra:
                total_compra = 0
                
                for idx, item in enumerate(st.session_state.itens_compra):
                    with st.container():
                        col_info, col_remove = st.columns([4, 1])
                        
                        with col_info:
                            st.markdown(f"""
                            **{item['nome']}**  
                            {item['quantidade']}x R$ {item['preco_unitario']:.2f} = R$ {item['subtotal']:.2f}
                            """)
                        
                        with col_remove:
                            if st.button("🗑️", key=f"remove_compra_{idx}"):
                                st.session_state.itens_compra.pop(idx)
                                st.rerun()
                        
                        st.divider()
                    
                    total_compra += item['subtotal']
                
                st.markdown(f"### Total: R$ {total_compra:.2f}")
                
                st.markdown("---")
                
                col_finalizar, col_limpar = st.columns(2)
                
                with col_finalizar:
                    if st.button("✅ Finalizar Compra", use_container_width=True, type="primary"):
                        if fornecedor and st.session_state.itens_compra:
                            try:
                                compra = CompraService.criar_compra(
                                    db=db,
                                    data_compra=data_compra,
                                    fornecedor=fornecedor,
                                    metodo_pagamento=metodo_pagamento,
                                    itens=st.session_state.itens_compra,
                                    observacoes=observacoes if observacoes else None
                                )
                                
                                st.success(f"✅ Compra #{compra.id} finalizada! Estoque atualizado.")
                                st.balloons()
                                st.session_state.itens_compra = []
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao finalizar compra: {str(e)}")
                        else:
                            st.warning("⚠️ Preencha o fornecedor e adicione pelo menos um item!")
                
                with col_limpar:
                    if st.button("🗑️ Limpar", use_container_width=True):
                        st.session_state.itens_compra = []
                        st.rerun()
            else:
                st.info("📋 Nenhum item adicionado")
    
    # HISTÓRICO DE COMPRAS
    elif opcao == "📋 Histórico de Compras":
        st.markdown("## 📋 Histórico de Compras")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            data_inicio = st.date_input(
                "Data Início",
                value=date.today().replace(day=1),
                key="data_inicio_compras"
            )
        
        with col2:
            data_fim = st.date_input(
                "Data Fim",
                value=date.today(),
                key="data_fim_compras"
            )
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            buscar = st.button("🔍 Buscar", use_container_width=True)
        
        if buscar or True:
            compras = CompraService.listar_compras(db, data_inicio, data_fim)
            
            if compras:
                st.markdown(f"**{len(compras)} compra(s) encontrada(s)**")
                
                # Estatísticas
                total_periodo = sum(float(c.valor_total) for c in compras)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Compras", len(compras))
                
                with col2:
                    st.metric("Valor Total", f"R$ {total_periodo:,.2f}")
                
                with col3:
                    ticket_medio = total_periodo / len(compras) if compras else 0
                    st.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
                
                st.divider()
                
                # Tabela de compras
                for compra in compras:
                    with st.expander(f"🛒 Compra #{compra.id} - {compra.data.strftime('%d/%m/%Y')} - R$ {float(compra.valor_total):.2f}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"""
                            **Fornecedor:** {compra.fornecedor}  
                            **Data:** {compra.data.strftime('%d/%m/%Y')}  
                            **Método:** {compra.metodo_pagamento}  
                            **Total:** R$ {float(compra.valor_total):.2f}
                            """)
                            
                            if compra.observacoes:
                                st.markdown(f"**Obs:** {compra.observacoes}")
                        
                        with col2:
                            st.markdown("**Itens:**")
                            for item in compra.itens:
                                st.markdown(f"""
                                - {item.produto.nome}: {item.quantidade}x R$ {float(item.preco_unitario):.2f} = R$ {float(item.subtotal):.2f}
                                """)
                
                # Exportar
                dados_compras = []
                for c in compras:
                    dados_compras.append({
                        'ID': c.id,
                        'Data': c.data.strftime('%d/%m/%Y'),
                        'Fornecedor': c.fornecedor,
                        'Valor': f"R$ {float(c.valor_total):.2f}",
                        'Pagamento': c.metodo_pagamento,
                        'Itens': len(c.itens)
                    })
                
                df_compras = pd.DataFrame(dados_compras)
                csv = df_compras.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Exportar Relatório",
                    data=csv,
                    file_name=f"compras_{data_inicio}_{data_fim}.csv",
                    mime="text/csv"
                )
            else:
                st.info("📊 Nenhuma compra encontrada no período selecionado.")

finally:
    db.close()