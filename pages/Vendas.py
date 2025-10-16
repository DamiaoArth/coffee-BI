import streamlit as st
import pandas as pd
from config.database import SessionLocal
from services.venda_service import VendaService
from services.produto_service import ProdutoService
from datetime import date, datetime
import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Por favor, faça login primeiro!")
    st.stop()

# Verificar se user existe e tem os dados necessários
if not st.session_state.user or 'username' not in st.session_state.user:
    st.error("❌ Erro de autenticação. Por favor, faça login novamente.")
    st.stop()

st.set_page_config(page_title="Vendas", page_icon="🧾", layout="wide")

st.markdown("# 🧾 Gerenciamento de Vendas")
st.markdown("---")

# Inicializar carrinho no session_state
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['username']}")
    st.divider()
    
    opcao = st.radio(
        "Selecione uma opção:",
        ["🛒 Nova Venda", "📋 Listar Vendas", "🔍 Consultar Venda"],
        label_visibility="collapsed"
    )

db = SessionLocal()

try:
    # NOVA VENDA
    if opcao == "🛒 Nova Venda":
        st.markdown("## 🛒 Registrar Nova Venda")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Adicionar Produtos")
            
            produtos = ProdutoService.listar_produtos(db, apenas_ativos=True)
            produtos_disponiveis = [p for p in produtos if p.estoque_atual > 0]
            
            if produtos_disponiveis:
                col_prod, col_qtd, col_btn = st.columns([3, 1, 1])
                
                with col_prod:
                    opcoes_produtos = {
                        f"{p.nome} - R$ {float(p.preco_venda):.2f} (Est: {p.estoque_atual})": p.id 
                        for p in produtos_disponiveis
                    }
                    
                    produto_selecionado = st.selectbox(
                        "Produto",
                        options=list(opcoes_produtos.keys()),
                        key="select_produto"
                    )
                
                with col_qtd:
                    quantidade = st.number_input(
                        "Quantidade",
                        min_value=1,
                        value=1,
                        step=1,
                        key="qtd_produto"
                    )
                
                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("➕ Adicionar", use_container_width=True):
                        produto_id = opcoes_produtos[produto_selecionado]
                        produto = ProdutoService.buscar_por_id(db, produto_id)
                        
                        if produto and produto.estoque_atual >= quantidade:
                            # Verificar se produto já está no carrinho
                            produto_no_carrinho = next(
                                (item for item in st.session_state.carrinho if item['id_produto'] == produto_id),
                                None
                            )
                            
                            if produto_no_carrinho:
                                nova_qtd = produto_no_carrinho['quantidade'] + quantidade
                                if nova_qtd <= produto.estoque_atual:
                                    produto_no_carrinho['quantidade'] = nova_qtd
                                    produto_no_carrinho['subtotal'] = float(produto.preco_venda) * nova_qtd
                                    st.success(f"✅ Quantidade atualizada!")
                                else:
                                    st.error(f"❌ Estoque insuficiente! Disponível: {produto.estoque_atual}")
                            else:
                                st.session_state.carrinho.append({
                                    'id_produto': produto.id,
                                    'nome': produto.nome,
                                    'quantidade': quantidade,
                                    'preco_unitario': float(produto.preco_venda),
                                    'subtotal': float(produto.preco_venda) * quantidade
                                })
                                st.success(f"✅ {produto.nome} adicionado ao carrinho!")
                            st.rerun()
                        else:
                            st.error(f"❌ Estoque insuficiente! Disponível: {produto.estoque_atual if produto else 0}")
            else:
                st.warning("⚠️ Nenhum produto disponível em estoque!")
        
        with col2:
            st.markdown("### 🛒 Carrinho")
            
            if st.session_state.carrinho:
                total_venda = 0
                
                for idx, item in enumerate(st.session_state.carrinho):
                    with st.container():
                        col_info, col_remove = st.columns([4, 1])
                        
                        with col_info:
                            st.markdown(f"""
                            **{item['nome']}**  
                            {item['quantidade']}x R$ {item['preco_unitario']:.2f} = R$ {item['subtotal']:.2f}
                            """)
                        
                        with col_remove:
                            if st.button("🗑️", key=f"remove_{idx}"):
                                st.session_state.carrinho.pop(idx)
                                st.rerun()
                        
                        st.divider()
                    
                    total_venda += item['subtotal']
                
                st.markdown(f"### Total: R$ {total_venda:.2f}")
                
                # Finalizar venda
                st.markdown("---")
                
                metodo_pagamento = st.selectbox(
                    "Método de Pagamento",
                    ["dinheiro", "cartão débito", "cartão crédito", "pix", "vale"]
                )
                
                observacoes = st.text_area("Observações (opcional)", placeholder="Ex: Cliente pediu sem açúcar")
                
                col_finalizar, col_limpar = st.columns(2)
                
                with col_finalizar:
                    if st.button("✅ Finalizar Venda", use_container_width=True, type="primary"):
                        try:
                            venda = VendaService.criar_venda(
                                db=db,
                                data_venda=date.today(),
                                metodo_pagamento=metodo_pagamento,
                                itens=st.session_state.carrinho,
                                observacoes=observacoes if observacoes else None,
                                funcionario_id=st.session_state.user.get('funcionario_id')
                            )
                            
                            st.success(f"✅ Venda #{venda.id} finalizada com sucesso!")
                            st.balloons()
                            st.session_state.carrinho = []
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao finalizar venda: {str(e)}")
                
                with col_limpar:
                    if st.button("🗑️ Limpar Carrinho", use_container_width=True):
                        st.session_state.carrinho = []
                        st.rerun()
            else:
                st.info("🛒 Carrinho vazio")
    
    # LISTAR VENDAS
    elif opcao == "📋 Listar Vendas":
        st.markdown("## 📋 Histórico de Vendas")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            data_inicio = st.date_input(
                "Data Início",
                value=date.today().replace(day=1),
                key="data_inicio_vendas"
            )
        
        with col2:
            data_fim = st.date_input(
                "Data Fim",
                value=date.today(),
                key="data_fim_vendas"
            )
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            buscar = st.button("🔍 Buscar", use_container_width=True)
        
        if buscar or True:  # Sempre mostra os resultados
            vendas = VendaService.listar_vendas(db, data_inicio, data_fim)
            
            if vendas:
                st.markdown(f"**{len(vendas)} venda(s) encontrada(s)**")
                
                # Estatísticas
                total_periodo = sum(float(v.valor_total) for v in vendas)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Vendas", len(vendas))
                
                with col2:
                    st.metric("Valor Total", f"R$ {total_periodo:,.2f}")
                
                with col3:
                    ticket_medio = total_periodo / len(vendas) if vendas else 0
                    st.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
                
                with col4:
                    vendas_hoje = [v for v in vendas if v.data == date.today()]
                    st.metric("Vendas Hoje", len(vendas_hoje))
                
                st.divider()
                
                # Tabela de vendas
                dados_vendas = []
                for v in vendas:
                    dados_vendas.append({
                        'ID': v.id,
                        'Data': v.data.strftime('%d/%m/%Y'),
                        'Hora': v.hora.strftime('%H:%M:%S') if v.hora else '-',
                        'Valor': f"R$ {float(v.valor_total):.2f}",
                        'Pagamento': v.metodo_pagamento,
                        'Itens': len(v.itens) if v.itens else 0
                    })
                
                df_vendas = pd.DataFrame(dados_vendas)
                
                # Selecionar venda para ver detalhes
                venda_selecionada = st.selectbox(
                    "Selecione uma venda para ver detalhes",
                    options=[f"Venda #{v['ID']} - {v['Data']} - {v['Valor']}" for v in dados_vendas],
                    key="select_venda_detalhe"
                )
                
                if venda_selecionada:
                    venda_id = int(venda_selecionada.split('#')[1].split(' ')[0])
                    venda = VendaService.buscar_por_id(db, venda_id)
                    
                    if venda:
                        with st.expander(f"📋 Detalhes da Venda #{venda.id}", expanded=True):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"""
                                **Data:** {venda.data.strftime('%d/%m/%Y')}  
                                **Hora:** {venda.hora.strftime('%H:%M:%S') if venda.hora else '-'}  
                                **Método:** {venda.metodo_pagamento}  
                                **Total:** R$ {float(venda.valor_total):.2f}
                                """)
                            
                            with col2:
                                if venda.observacoes:
                                    st.markdown(f"**Observações:** {venda.observacoes}")
                                if venda.funcionario:
                                    st.markdown(f"**Vendedor:** {venda.funcionario.nome}")
                            
                            st.markdown("#### Itens da Venda")
                            
                            itens_data = []
                            for item in venda.itens:
                                itens_data.append({
                                    'Produto': item.produto.nome,
                                    'Quantidade': item.quantidade,
                                    'Preço Unit.': f"R$ {float(item.preco_unitario):.2f}",
                                    'Subtotal': f"R$ {float(item.subtotal):.2f}"
                                })
                            
                            df_itens = pd.DataFrame(itens_data)
                            st.dataframe(df_itens, use_container_width=True, hide_index=True)
                            
                            # Opção de cancelar venda (apenas admin)
                            if st.session_state.user['nivel_acesso'] == 'admin':
                                st.divider()
                                if st.button(f"🗑️ Cancelar Venda #{venda.id}", type="secondary"):
                                    if st.checkbox(f"Confirmo que desejo cancelar a venda #{venda.id}"):
                                        if VendaService.cancelar_venda(db, venda.id):
                                            st.success("✅ Venda cancelada e estoque devolvido!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Erro ao cancelar venda.")
                
                # Exportar relatório
                st.divider()
                csv = df_vendas.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Exportar Relatório",
                    data=csv,
                    file_name=f"vendas_{data_inicio}_{data_fim}.csv",
                    mime="text/csv"
                )
            else:
                st.info("📊 Nenhuma venda encontrada no período selecionado.")
    
    # CONSULTAR VENDA
    elif opcao == "🔍 Consultar Venda":
        st.markdown("## 🔍 Consultar Venda por ID")
        
        venda_id = st.number_input(
            "Digite o ID da Venda",
            min_value=1,
            value=1,
            step=1,
            key="busca_venda_id"
        )
        
        if st.button("🔍 Buscar Venda"):
            venda = VendaService.buscar_por_id(db, venda_id)
            
            if venda:
                st.success(f"✅ Venda #{venda.id} encontrada!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Informações da Venda")
                    st.markdown(f"""
                    **ID:** {venda.id}  
                    **Data:** {venda.data.strftime('%d/%m/%Y')}  
                    **Hora:** {venda.hora.strftime('%H:%M:%S') if venda.hora else '-'}  
                    **Método Pagamento:** {venda.metodo_pagamento}  
                    **Valor Total:** R$ {float(venda.valor_total):.2f}
                    """)
                    
                    if venda.observacoes:
                        st.markdown(f"**Observações:** {venda.observacoes}")
                    
                    if venda.funcionario:
                        st.markdown(f"**Vendedor:** {venda.funcionario.nome}")
                
                with col2:
                    st.markdown("### Itens da Venda")
                    
                    for item in venda.itens:
                        st.markdown(f"""
                        **{item.produto.nome}**  
                        Quantidade: {item.quantidade}  
                        Preço Unit.: R$ {float(item.preco_unitario):.2f}  
                        Subtotal: R$ {float(item.subtotal):.2f}
                        """)
                        st.divider()
                
                # Opção de cancelar (apenas admin)
                if st.session_state.user['nivel_acesso'] == 'admin':
                    st.markdown("---")
                    st.warning("⚠️ Área Administrativa")
                    
                    if st.button(f"🗑️ Cancelar Venda #{venda.id}", type="secondary"):
                        confirmar = st.checkbox(f"Confirmo que desejo cancelar a venda #{venda.id}")
                        
                        if confirmar:
                            if VendaService.cancelar_venda(db, venda.id):
                                st.success("✅ Venda cancelada e estoque devolvido!")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao cancelar venda.")
            else:
                st.error(f"❌ Venda #{venda_id} não encontrada!")

finally:
    db.close()
