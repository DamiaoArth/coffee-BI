import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config.database import SessionLocal
from services.relatorio_service import RelatorioService
from services.produto_service import ProdutoService
from datetime import date, timedelta, datetime
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

st.set_page_config(page_title="BI Dashboard", page_icon="📊", layout="wide")

# CSS customizado para o dashboard
st.markdown("""
<style>
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .chart-container {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# 📊 Business Intelligence Dashboard")
st.markdown("### Análise Completa de Dados da Cafeteria")
st.markdown("---")

db = SessionLocal()

try:
    # Sidebar para filtros
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['username']}")
        st.divider()
        
        st.markdown("### 📅 Período de Análise")
        
        periodo_preset = st.selectbox(
            "Período Rápido",
            ["Hoje", "Última Semana", "Último Mês", "Últimos 3 Meses", "Este Ano", "Personalizado"]
        )
        
        hoje = date.today()
        
        if periodo_preset == "Hoje":
            data_inicio = data_fim = hoje
        elif periodo_preset == "Última Semana":
            data_inicio = hoje - timedelta(days=7)
            data_fim = hoje
        elif periodo_preset == "Último Mês":
            data_inicio = hoje - timedelta(days=30)
            data_fim = hoje
        elif periodo_preset == "Últimos 3 Meses":
            data_inicio = hoje - timedelta(days=90)
            data_fim = hoje
        elif periodo_preset == "Este Ano":
            data_inicio = date(hoje.year, 1, 1)
            data_fim = hoje
        else:
            data_inicio = st.date_input("Data Início", value=hoje - timedelta(days=30))
            data_fim = st.date_input("Data Fim", value=hoje)
        
        st.divider()
        
        # Filtros adicionais
        st.markdown("### 🔍 Filtros")
        mostrar_graficos = st.multiselect(
            "Gráficos para Exibir",
            ["Vendas", "Produtos", "Categorias", "Pagamentos", "Fluxo de Caixa", "Lucratividade"],
            default=["Vendas", "Produtos", "Categorias", "Pagamentos"]
        )
    
    # MÉTRICAS PRINCIPAIS
    st.markdown("## 📈 Indicadores Principais")
    
    # Buscar dados
    df_vendas = RelatorioService.vendas_por_periodo(db, data_inicio, data_fim)
    
    if not df_vendas.empty:
        total_vendas = df_vendas['Total'].sum()
        qtd_vendas = df_vendas['Quantidade'].sum()
        ticket_medio = total_vendas / qtd_vendas if qtd_vendas > 0 else 0
        
        # Comparar com período anterior
        dias_periodo = (data_fim - data_inicio).days + 1
        data_inicio_anterior = data_inicio - timedelta(days=dias_periodo)
        data_fim_anterior = data_inicio - timedelta(days=1)
        
        df_vendas_anterior = RelatorioService.vendas_por_periodo(db, data_inicio_anterior, data_fim_anterior)
        total_anterior = df_vendas_anterior['Total'].sum() if not df_vendas_anterior.empty else 0
        
        variacao = ((total_vendas - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0
        
        # Exibir métricas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💰 Faturamento Total",
                value=f"R$ {total_vendas:,.2f}",
                delta=f"{variacao:+.1f}% vs período anterior"
            )
        
        with col2:
            st.metric(
                label="🧾 Total de Vendas",
                value=int(qtd_vendas),
                delta=f"{'📈' if qtd_vendas > 0 else '📉'}"
            )
        
        with col3:
            st.metric(
                label="🎯 Ticket Médio",
                value=f"R$ {ticket_medio:.2f}",
                delta=f"{dias_periodo} dias"
            )
        
        with col4:
            # Produtos com estoque baixo
            produtos_baixo = ProdutoService.produtos_estoque_baixo(db)
            st.metric(
                label="⚠️ Alertas de Estoque",
                value=len(produtos_baixo),
                delta="Atenção" if len(produtos_baixo) > 0 else "OK",
                delta_color="inverse" if len(produtos_baixo) > 0 else "normal"
            )
        
        st.markdown("---")
        
        # GRÁFICO DE VENDAS AO LONGO DO TEMPO
        if "Vendas" in mostrar_graficos:
            st.markdown("## 📈 Evolução das Vendas")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig_vendas = go.Figure()
                
                fig_vendas.add_trace(go.Scatter(
                    x=df_vendas['Data'],
                    y=df_vendas['Total'],
                    mode='lines+markers',
                    name='Faturamento',
                    line=dict(color='#667eea', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(102, 126, 234, 0.1)'
                ))
                
                fig_vendas.update_layout(
                    title="Faturamento Diário",
                    xaxis_title="Data",
                    yaxis_title="Valor (R$)",
                    height=400,
                    hovermode='x unified',
                    showlegend=False
                )
                
                st.plotly_chart(fig_vendas, use_container_width=True)
            
            with col2:
                # Estatísticas do período
                st.markdown("### 📊 Estatísticas")
                st.metric("Maior Venda", f"R$ {df_vendas['Total'].max():.2f}")
                st.metric("Menor Venda", f"R$ {df_vendas['Total'].min():.2f}")
                st.metric("Média Diária", f"R$ {df_vendas['Total'].mean():.2f}")
                
                # Dia com mais vendas
                dia_max = df_vendas.loc[df_vendas['Total'].idxmax(), 'Data']
                st.info(f"🏆 Melhor dia: {dia_max.strftime('%d/%m/%Y')}")
        
        # PRODUTOS MAIS VENDIDOS
        if "Produtos" in mostrar_graficos:
            st.markdown("## 🏆 Top Produtos Mais Vendidos")
            
            df_produtos = RelatorioService.produtos_mais_vendidos(db, data_inicio, data_fim, top=10)
            
            if not df_produtos.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_produtos_bar = px.bar(
                        df_produtos,
                        x='Quantidade',
                        y='Produto',
                        orientation='h',
                        title='Quantidade Vendida',
                        color='Quantidade',
                        color_continuous_scale='Blues'
                    )
                    fig_produtos_bar.update_layout(
                        height=400,
                        showlegend=False,
                        yaxis={'categoryorder': 'total ascending'}
                    )
                    st.plotly_chart(fig_produtos_bar, use_container_width=True)
                
                with col2:
                    fig_produtos_pie = px.pie(
                        df_produtos.head(5),
                        values='Total',
                        names='Produto',
                        title='Top 5 - Participação no Faturamento',
                        color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    fig_produtos_pie.update_traces(
                        textposition='inside',
                        textinfo='percent+label'
                    )
                    fig_produtos_pie.update_layout(height=400)
                    st.plotly_chart(fig_produtos_pie, use_container_width=True)
                
                # Tabela detalhada
                with st.expander("📋 Ver Tabela Detalhada"):
                    st.dataframe(
                        df_produtos.style.format({
                            'Total': 'R$ {:,.2f}',
                            'Quantidade': '{:,}'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.info("📊 Nenhum dado de produtos disponível para o período.")
        
        # VENDAS POR CATEGORIA
        if "Categorias" in mostrar_graficos:
            st.markdown("## 📦 Análise por Categoria")
            
            df_categorias = RelatorioService.vendas_por_categoria(db, data_inicio, data_fim)
            
            if not df_categorias.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_cat_pie = px.pie(
                        df_categorias,
                        values='Total',
                        names='Categoria',
                        title='Faturamento por Categoria',
                        hole=0.4,
                        color_discrete_sequence=px.colors.sequential.Sunset
                    )
                    fig_cat_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_cat_pie.update_layout(height=400)
                    st.plotly_chart(fig_cat_pie, use_container_width=True)
                
                with col2:
                    fig_cat_bar = px.bar(
                        df_categorias,
                        x='Categoria',
                        y='Quantidade',
                        title='Quantidade Vendida por Categoria',
                        color='Quantidade',
                        color_continuous_scale='Viridis'
                    )
                    fig_cat_bar.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig_cat_bar, use_container_width=True)
                
                # Insights
                categoria_top = df_categorias.loc[df_categorias['Total'].idxmax()]
                st.success(f"🎯 **Categoria Líder:** {categoria_top['Categoria']} com R$ {float(categoria_top['Total']):.2f} em vendas")
        
        # MÉTODOS DE PAGAMENTO
        if "Pagamentos" in mostrar_graficos:
            st.markdown("## 💳 Análise de Formas de Pagamento")
            
            df_pagamentos = RelatorioService.vendas_por_metodo_pagamento(db, data_inicio, data_fim)
            
            if not df_pagamentos.empty:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    fig_pag = px.funnel(
                        df_pagamentos,
                        x='Total',
                        y='Método',
                        title='Faturamento por Método de Pagamento',
                        color='Total',
                        color_continuous_scale='Greens'
                    )
                    fig_pag.update_layout(height=400)
                    st.plotly_chart(fig_pag, use_container_width=True)
                
                with col2:
                    # Criar gráfico de barras horizontal
                    fig_pag_bar = go.Figure()
                    
                    fig_pag_bar.add_trace(go.Bar(
                        x=df_pagamentos['Quantidade'],
                        y=df_pagamentos['Método'],
                        orientation='h',
                        marker=dict(
                            color=df_pagamentos['Total'],
                            colorscale='Blues',
                            showscale=True
                        ),
                        text=df_pagamentos['Quantidade'],
                        textposition='auto'
                    ))
                    
                    fig_pag_bar.update_layout(
                        title='Quantidade de Transações por Método',
                        xaxis_title='Quantidade',
                        yaxis_title='Método',
                        height=400
                    )
                    st.plotly_chart(fig_pag_bar, use_container_width=True)
        
        # FLUXO DE CAIXA
        if "Fluxo de Caixa" in mostrar_graficos:
            st.markdown("## 💰 Fluxo de Caixa")
            
            df_fluxo = RelatorioService.fluxo_caixa(db, data_inicio, data_fim)
            
            if not df_fluxo.empty:
                # Gráfico de fluxo de caixa
                fig_fluxo = go.Figure()
                
                fig_fluxo.add_trace(go.Bar(
                    name='Entradas',
                    x=df_fluxo['data'],
                    y=df_fluxo['entrada'],
                    marker_color='green'
                ))
                
                fig_fluxo.add_trace(go.Bar(
                    name='Saídas',
                    x=df_fluxo['data'],
                    y=df_fluxo['saida'],
                    marker_color='red'
                ))
                
                fig_fluxo.add_trace(go.Scatter(
                    name='Saldo Acumulado',
                    x=df_fluxo['data'],
                    y=df_fluxo['saldo_acumulado'],
                    mode='lines+markers',
                    line=dict(color='blue', width=3),
                    yaxis='y2'
                ))
                
                fig_fluxo.update_layout(
                    title='Fluxo de Caixa Detalhado',
                    xaxis_title='Data',
                    yaxis_title='Valor (R$)',
                    yaxis2=dict(
                        title='Saldo Acumulado (R$)',
                        overlaying='y',
                        side='right'
                    ),
                    barmode='group',
                    height=500,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_fluxo, use_container_width=True)
                
                # Métricas do fluxo
                col1, col2, col3, col4 = st.columns(4)
                
                total_entradas = df_fluxo['entrada'].sum()
                total_saidas = df_fluxo['saida'].sum()
                saldo_final = df_fluxo['saldo_acumulado'].iloc[-1] if len(df_fluxo) > 0 else 0
                
                with col1:
                    st.metric("💵 Total Entradas", f"R$ {total_entradas:,.2f}")
                
                with col2:
                    st.metric("💸 Total Saídas", f"R$ {total_saidas:,.2f}")
                
                with col3:
                    saldo_periodo = total_entradas - total_saidas
                    st.metric(
                        "📊 Saldo Período",
                        f"R$ {saldo_periodo:,.2f}",
                        delta="Positivo" if saldo_periodo > 0 else "Negativo"
                    )
                
                with col4:
                    st.metric("🏦 Saldo Acumulado", f"R$ {saldo_final:,.2f}")
            else:
                st.info("📊 Nenhum dado de fluxo de caixa disponível.")
        
        # ANÁLISE DE LUCRATIVIDADE
        if "Lucratividade" in mostrar_graficos:
            st.markdown("## 💎 Análise de Lucratividade")
            
            df_lucro = RelatorioService.lucro_por_produto(db, data_inicio, data_fim)
            
            if not df_lucro.empty:
                # Top 10 produtos mais lucrativos
                df_lucro_top = df_lucro.nlargest(10, 'Lucro')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_lucro = px.bar(
                        df_lucro_top,
                        x='Produto',
                        y=['Receita', 'Custo', 'Lucro'],
                        title='Top 10 Produtos - Análise de Lucratividade',
                        barmode='group',
                        color_discrete_map={
                            'Receita': '#2ecc71',
                            'Custo': '#e74c3c',
                            'Lucro': '#3498db'
                        }
                    )
                    fig_lucro.update_layout(
                        height=400,
                        xaxis_tickangle=-45
                    )
                    st.plotly_chart(fig_lucro, use_container_width=True)
                
                with col2:
                    fig_margem = px.bar(
                        df_lucro_top,
                        x='Produto',
                        y='Margem %',
                        title='Margem de Lucro (%)',
                        color='Margem %',
                        color_continuous_scale='RdYlGn'
                    )
                    fig_margem.update_layout(
                        height=400,
                        xaxis_tickangle=-45,
                        showlegend=False
                    )
                    st.plotly_chart(fig_margem, use_container_width=True)
                
                # Métricas de lucratividade
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    lucro_total = df_lucro['Lucro'].sum()
                    st.metric("💰 Lucro Total", f"R$ {lucro_total:,.2f}")
                
                with col2:
                    receita_total = df_lucro['Receita'].sum()
                    margem_geral = (lucro_total / receita_total * 100) if receita_total > 0 else 0
                    st.metric("📊 Margem Geral", f"{margem_geral:.1f}%")
                
                with col3:
                    produto_mais_lucrativo = df_lucro.loc[df_lucro['Lucro'].idxmax()]
                    st.metric("🏆 Produto Mais Lucrativo", produto_mais_lucrativo['Produto'])
                
                # Tabela completa de lucratividade
                with st.expander("📋 Ver Análise Completa de Lucratividade"):
                    st.dataframe(
                        df_lucro.style.format({
                            'Receita': 'R$ {:,.2f}',
                            'Custo': 'R$ {:,.2f}',
                            'Lucro': 'R$ {:,.2f}',
                            'Margem %': '{:.2f}%'
                        }).background_gradient(subset=['Margem %'], cmap='RdYlGn'),
                        use_container_width=True,
                        hide_index=True
                    )
        
        # SEÇÃO DE EXPORTAÇÃO
        st.markdown("---")
        st.markdown("## 📥 Exportar Relatórios")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if not df_vendas.empty:
                csv_vendas = df_vendas.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📊 Exportar Vendas (CSV)",
                    data=csv_vendas,
                    file_name=f"vendas_{data_inicio}_{data_fim}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col2:
            if "Produtos" in mostrar_graficos and not df_produtos.empty:
                csv_produtos = df_produtos.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="🏆 Exportar Top Produtos (CSV)",
                    data=csv_produtos,
                    file_name=f"produtos_{data_inicio}_{data_fim}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col3:
            if "Lucratividade" in mostrar_graficos and not df_lucro.empty:
                csv_lucro = df_lucro.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="💎 Exportar Lucratividade (CSV)",
                    data=csv_lucro,
                    file_name=f"lucratividade_{data_inicio}_{data_fim}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        # INSIGHTS AUTOMÁTICOS
        st.markdown("---")
        st.markdown("## 🤖 Insights Automáticos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Oportunidades")
            
            # Produtos com boa margem mas baixa venda
            if not df_lucro.empty:
                produtos_oportunidade = df_lucro[
                    (df_lucro['Margem %'] > 50) & 
                    (df_lucro['Quantidade'] < df_lucro['Quantidade'].median())
                ].head(3)
                
                if not produtos_oportunidade.empty:
                    st.success("💡 **Produtos com alta margem e baixa venda:**")
                    for _, prod in produtos_oportunidade.iterrows():
                        st.markdown(f"- **{prod['Produto']}**: Margem {prod['Margem %']:.1f}% - Considere promover!")
                else:
                    st.info("Nenhuma oportunidade identificada no momento.")
        
        with col2:
            st.markdown("### ⚠️ Alertas")
            
            # Produtos com estoque baixo
            produtos_baixo = ProdutoService.produtos_estoque_baixo(db)
            if produtos_baixo:
                st.warning(f"📦 **{len(produtos_baixo)} produto(s) com estoque baixo:**")
                for prod in produtos_baixo[:5]:
                    st.markdown(f"- **{prod.nome}**: {prod.estoque_atual} {prod.unidade} (mín: {prod.estoque_minimo})")
            else:
                st.success("✅ Todos os produtos com estoque adequado!")
    
    else:
        st.info("📊 Nenhuma venda registrada no período selecionado. Selecione outro período ou registre vendas primeiro.")

except Exception as e:
    st.error(f"❌ Erro ao carregar dashboard: {str(e)}")
    st.exception(e)

finally:
    db.close()
