import streamlit as st
import pandas as pd
from config.database import SessionLocal
from models.database_models import Transacao
from datetime import date
import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Por favor, faça login primeiro!")
    st.stop()

# Verificar se user existe e tem os dados necessários
if not st.session_state.user or 'nivel_acesso' not in st.session_state.user:
    st.error("❌ Erro de autenticação. Por favor, faça login novamente.")
    st.stop()

# Verificar se é admin
if st.session_state.user['nivel_acesso'] != 'admin':
    st.error("❌ Acesso negado! Apenas administradores podem acessar esta página.")
    st.stop()

st.set_page_config(page_title="Financeiro", page_icon="💰", layout="wide")

st.markdown("# 💰 Gerenciamento Financeiro")
st.markdown("### Controle de Receitas e Despesas")
st.markdown("---")

with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['username']}")
    st.divider()
    
    opcao = st.radio(
        "Selecione uma opção:",
        ["➕ Nova Transação", "📋 Extrato", "📊 Relatórios"],
        label_visibility="collapsed"
    )

db = SessionLocal()

try:
    # NOVA TRANSAÇÃO
    if opcao == "➕ Nova Transação":
        st.markdown("## ➕ Registrar Nova Transação")
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("form_transacao", clear_on_submit=True):
                tipo = st.selectbox(
                    "Tipo de Transação*",
                    ["entrada", "saída"]
                )
                
                descricao = st.text_input(
                    "Descrição*",
                    placeholder="Ex: Pagamento de conta de luz"
                )
                
                valor = st.number_input(
                    "Valor (R$)*",
                    min_value=0.01,
                    value=100.00,
                    step=10.00,
                    format="%.2f"
                )
                
                # Categorias diferentes para entrada e saída
                if tipo == "entrada":
                    categorias = [
                        "venda",
                        "investimento",
                        "empréstimo",
                        "doação",
                        "outro"
                    ]
                else:
                    categorias = [
                        "aluguel",
                        "água",
                        "luz",
                        "internet",
                        "telefone",
                        "salário",
                        "insumo",
                        "manutenção",
                        "marketing",
                        "impostos",
                        "outro"
                    ]
                
                categoria = st.selectbox("Categoria*", categorias)
                
                data_transacao = st.date_input(
                    "Data*",
                    value=date.today()
                )
                
                submit = st.form_submit_button(
                    "💾 Registrar Transação",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit:
                    if descricao and valor > 0:
                        try:
                            transacao = Transacao(
                                tipo=tipo,
                                descricao=descricao,
                                valor=valor,
                                data=data_transacao,
                                categoria=categoria
                            )
                            db.add(transacao)
                            db.commit()
                            
                            st.success(f"✅ Transação registrada com sucesso!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Erro ao registrar transação: {str(e)}")
                    else:
                        st.warning("⚠️ Preencha todos os campos obrigatórios!")
        
        with col2:
            st.markdown("### 💡 Dicas")
            st.info("""
            **Entradas:** Receitas que entram no caixa  
            - Vendas já são registradas automaticamente  
            - Use para registrar outras receitas
            
            **Saídas:** Despesas que saem do caixa  
            - Aluguel, contas, salários, etc.  
            - Compras são registradas automaticamente
            
            ⚠️ **Importante:** Mantenha o controle atualizado para análises precisas!
            """)
            
            # Resumo rápido do dia
            hoje = date.today()
            transacoes_hoje = db.query(Transacao).filter(
                Transacao.data == hoje
            ).all()
            
            if transacoes_hoje:
                entradas_hoje = sum(float(t.valor) for t in transacoes_hoje if t.tipo == 'entrada')
                saidas_hoje = sum(float(t.valor) for t in transacoes_hoje if t.tipo == 'saída')
                saldo_hoje = entradas_hoje - saidas_hoje
                
                st.markdown("### 📊 Resumo de Hoje")
                st.metric("Entradas", f"R$ {entradas_hoje:,.2f}")
                st.metric("Saídas", f"R$ {saidas_hoje:,.2f}")
                st.metric("Saldo", f"R$ {saldo_hoje:,.2f}")
    
    # EXTRATO
    elif opcao == "📋 Extrato":
        st.markdown("## 📋 Extrato de Transações")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            data_inicio = st.date_input(
                "Data Início",
                value=date.today().replace(day=1)
            )
        
        with col2:
            data_fim = st.date_input(
                "Data Fim",
                value=date.today()
            )
        
        with col3:
            filtro_tipo = st.selectbox(
                "Tipo",
                ["Todos", "entrada", "saída"]
            )
        
        with col4:
            filtro_categoria = st.text_input(
                "Categoria",
                placeholder="Digite para filtrar"
            )
        
        # Buscar transações
        query = db.query(Transacao).filter(
            Transacao.data >= data_inicio,
            Transacao.data <= data_fim
        )
        
        if filtro_tipo != "Todos":
            query = query.filter(Transacao.tipo == filtro_tipo)
        
        if filtro_categoria:
            query = query.filter(Transacao.categoria.contains(filtro_categoria))
        
        transacoes = query.order_by(Transacao.data.desc()).all()
        
        if transacoes:
            # Métricas do período
            entradas = sum(float(t.valor) for t in transacoes if t.tipo == 'entrada')
            saidas = sum(float(t.valor) for t in transacoes if t.tipo == 'saída')
            saldo = entradas - saidas
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("💵 Entradas", f"R$ {entradas:,.2f}")
            
            with col2:
                st.metric("💸 Saídas", f"R$ {saidas:,.2f}")
            
            with col3:
                st.metric(
                    "📊 Saldo",
                    f"R$ {saldo:,.2f}",
                    delta="Positivo" if saldo > 0 else "Negativo"
                )
            
            with col4:
                st.metric("📋 Transações", len(transacoes))
            
            st.divider()
            
            # Tabela de transações
            dados_transacoes = []
            for t in transacoes:
                dados_transacoes.append({
                    'ID': t.id,
                    'Data': t.data.strftime('%d/%m/%Y'),
                    'Tipo': '💵 Entrada' if t.tipo == 'entrada' else '💸 Saída',
                    'Descrição': t.descricao,
                    'Categoria': t.categoria,
                    'Valor': f"R$ {float(t.valor):,.2f}"
                })
            
            df = pd.DataFrame(dados_transacoes)
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Opções de ação
            col1, col2 = st.columns([4, 1])
            
            with col2:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Exportar CSV",
                    data=csv,
                    file_name=f"extrato_{data_inicio}_{data_fim}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # Excluir transação
            st.divider()
            st.markdown("### 🗑️ Excluir Transação")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                transacao_id = st.number_input(
                    "ID da Transação",
                    min_value=1,
                    step=1,
                    key="id_excluir"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Excluir", use_container_width=True):
                    transacao = db.query(Transacao).filter(
                        Transacao.id == transacao_id
                    ).first()
                    
                    if transacao:
                        if st.checkbox(f"Confirmo a exclusão da transação #{transacao_id}"):
                            db.delete(transacao)
                            db.commit()
                            st.success("✅ Transação excluída!")
                            st.rerun()
                    else:
                        st.error("❌ Transação não encontrada!")
        else:
            st.info("📊 Nenhuma transação encontrada no período.")
    
    # RELATÓRIOS
    elif opcao == "📊 Relatórios":
        st.markdown("## 📊 Relatórios Financeiros")
        
        col1, col2 = st.columns(2)
        
        with col1:
            data_inicio = st.date_input(
                "Data Início",
                value=date.today().replace(day=1)
            )
        
        with col2:
            data_fim = st.date_input(
                "Data Fim",
                value=date.today()
            )
        
        transacoes = db.query(Transacao).filter(
            Transacao.data >= data_inicio,
            Transacao.data <= data_fim
        ).all()
        
        if transacoes:
            import plotly.express as px
            import plotly.graph_objects as go
            
            # Preparar dados
            df_transacoes = pd.DataFrame([{
                'data': t.data,
                'tipo': t.tipo,
                'valor': float(t.valor),
                'categoria': t.categoria
            } for t in transacoes])
            
            # Gráfico de entradas vs saídas
            st.markdown("### 💰 Entradas vs Saídas")
            
            resumo_tipo = df_transacoes.groupby('tipo')['valor'].sum().reset_index()
            
            fig_tipo = px.pie(
                resumo_tipo,
                values='valor',
                names='tipo',
                title='Distribuição: Entradas x Saídas',
                color='tipo',
                color_discrete_map={'entrada': 'green', 'saída': 'red'}
            )
            st.plotly_chart(fig_tipo, use_container_width=True)
            
            # Gráfico por categoria
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📊 Entradas por Categoria")
                entradas = df_transacoes[df_transacoes['tipo'] == 'entrada']
                if not entradas.empty:
                    resumo_cat_entrada = entradas.groupby('categoria')['valor'].sum().reset_index()
                    fig_cat_e = px.bar(
                        resumo_cat_entrada,
                        x='categoria',
                        y='valor',
                        color='valor',
                        color_continuous_scale='Greens'
                    )
                    fig_cat_e.update_layout(showlegend=False)
                    st.plotly_chart(fig_cat_e, use_container_width=True)
                else:
                    st.info("Sem entradas no período")
            
            with col2:
                st.markdown("### 📊 Saídas por Categoria")
                saidas = df_transacoes[df_transacoes['tipo'] == 'saída']
                if not saidas.empty:
                    resumo_cat_saida = saidas.groupby('categoria')['valor'].sum().reset_index()
                    fig_cat_s = px.bar(
                        resumo_cat_saida,
                        x='categoria',
                        y='valor',
                        color='valor',
                        color_continuous_scale='Reds'
                    )
                    fig_cat_s.update_layout(showlegend=False)
                    st.plotly_chart(fig_cat_s, use_container_width=True)
                else:
                    st.info("Sem saídas no período")
            
            # Evolução diária
            st.markdown("### 📈 Evolução Diária")
            
            evolucao = df_transacoes.groupby(['data', 'tipo'])['valor'].sum().reset_index()
            evolucao_pivot = evolucao.pivot(index='data', columns='tipo', values='valor').fillna(0)
            evolucao_pivot['saldo'] = evolucao_pivot.get('entrada', 0) - evolucao_pivot.get('saída', 0)
            evolucao_pivot['saldo_acumulado'] = evolucao_pivot['saldo'].cumsum()
            evolucao_pivot = evolucao_pivot.reset_index()
            
            fig_evolucao = go.Figure()
            
            if 'entrada' in evolucao_pivot.columns:
                fig_evolucao.add_trace(go.Bar(
                    name='Entradas',
                    x=evolucao_pivot['data'],
                    y=evolucao_pivot['entrada'],
                    marker_color='green'
                ))
            
            if 'saída' in evolucao_pivot.columns:
                fig_evolucao.add_trace(go.Bar(
                    name='Saídas',
                    x=evolucao_pivot['data'],
                    y=evolucao_pivot['saída'],
                    marker_color='red'
                ))
            
            fig_evolucao.add_trace(go.Scatter(
                name='Saldo Acumulado',
                x=evolucao_pivot['data'],
                y=evolucao_pivot['saldo_acumulado'],
                mode='lines+markers',
                line=dict(color='blue', width=3),
                yaxis='y2'
            ))
            
            fig_evolucao.update_layout(
                title='Fluxo de Caixa Diário',
                xaxis_title='Data',
                yaxis_title='Valor (R$)',
                yaxis2=dict(
                    title='Saldo Acumulado (R$)',
                    overlaying='y',
                    side='right'
                ),
                barmode='group',
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_evolucao, use_container_width=True)
            
            # Resumo estatístico
            st.markdown("### 📊 Resumo Estatístico")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### Entradas")
                if not entradas.empty:
                    st.metric("Total", f"R$ {entradas['valor'].sum():,.2f}")
                    st.metric("Média", f"R$ {entradas['valor'].mean():.2f}")
                    st.metric("Maior", f"R$ {entradas['valor'].max():.2f}")
            
            with col2:
                st.markdown("#### Saídas")
                if not saidas.empty:
                    st.metric("Total", f"R$ {saidas['valor'].sum():,.2f}")
                    st.metric("Média", f"R$ {saidas['valor'].mean():.2f}")
                    st.metric("Maior", f"R$ {saidas['valor'].max():.2f}")
            
            with col3:
                st.markdown("#### Saldo")
                saldo_total = entradas['valor'].sum() - saidas['valor'].sum() if not entradas.empty and not saidas.empty else 0
                st.metric(
                    "Saldo Período",
                    f"R$ {saldo_total:,.2f}",
                    delta="Positivo" if saldo_total > 0 else "Negativo"
                )
                st.metric("Total Transações", len(df_transacoes))
        else:
            st.info("📊 Nenhuma transação encontrada no período selecionado.")

finally:
    db.close()
