import streamlit as st
from config.database import init_db, SessionLocal
from services.auth_service import AuthService
from models.database_models import Usuario
import sys
from pathlib import Path

# Configuração da página
st.set_page_config(
    page_title="ERP Cafeteria",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Adicionar o diretório raiz ao path
root_path = Path(__file__).parent
sys.path.append(str(root_path))

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #6F4E37;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #6F4E37;
    }
    .stAlert {
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar banco de dados
@st.cache_resource
def initialize_database():
    init_db()
    db = SessionLocal()
    
    # Criar usuário admin padrão se não existir
    admin_exists = db.query(Usuario).filter(Usuario.nome_usuario == "admin").first()
    if not admin_exists:
        AuthService.criar_usuario(
            db=db,
            nome_usuario="admin",
            senha="admin123",
            nivel_acesso="admin"
        )
        st.success("✅ Usuário admin criado! Login: admin | Senha: admin123")
    
    db.close()

# Inicializar session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'db_initialized' not in st.session_state:
    initialize_database()
    st.session_state.db_initialized = True

# Função de login
def login_page():
    st.markdown('<p class="main-header">☕ ERP Cafeteria</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Usuário", placeholder="Digite seu usuário")
            password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            submit = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit:
                if username and password:
                    db = SessionLocal()
                    user = AuthService.authenticate(db, username, password)
                    
                    if user:
                        # Extrair todos os dados do usuário ANTES de fechar a sessão
                        user_data = {
                            'id': user.id,
                            'username': user.nome_usuario,
                            'nivel_acesso': user.nivel_acesso,
                            'funcionario_id': user.funcionario_id
                        }
                        db.close()  # Fechar a sessão aqui
                        
                        st.session_state.authenticated = True
                        st.session_state.user = user_data
                        st.rerun()
                    else:
                        db.close()
                        st.error("❌ Usuário ou senha inválidos!")
                else:
                    st.warning("⚠️ Por favor, preencha todos os campos!")
        
        st.divider() 

# Função de logout
def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

# Página principal (Dashboard)
def main_page():
    st.markdown('<p class="main-header">☕ Sistema ERP - Cafeteria</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['username']}")
        st.markdown(f"**Nível:** {st.session_state.user['nivel_acesso'].upper()}")
        st.divider()
        
        if st.button("🚪 Sair", use_container_width=True):
            logout()
    
    # Dashboard principal
    st.markdown("## 📊 Dashboard Geral")
    
    db = SessionLocal()
    
    try:
        from services.produto_service import ProdutoService
        from services.relatorio_service import RelatorioService
        from datetime import date, timedelta
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        hoje = date.today()
        inicio_mes = date(hoje.year, hoje.month, 1)
        
        # Total de vendas do mês
        vendas_mes = RelatorioService.vendas_por_periodo(db, inicio_mes, hoje)
        total_vendas = vendas_mes['Total'].sum() if not vendas_mes.empty else 0
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                label="💰 Vendas do Mês",
                value=f"R$ {total_vendas:,.2f}",
                delta=f"{len(vendas_mes)} vendas"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Produtos em estoque baixo
        produtos_baixo = ProdutoService.produtos_estoque_baixo(db)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                label="⚠️ Estoque Baixo",
                value=len(produtos_baixo),
                delta="produtos" if len(produtos_baixo) != 1 else "produto",
                delta_color="inverse"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Total de produtos ativos
        produtos_ativos = len(ProdutoService.listar_produtos(db))
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                label="📦 Produtos Ativos",
                value=produtos_ativos,
                delta="cadastrados"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Vendas hoje
        vendas_hoje = RelatorioService.vendas_por_periodo(db, hoje, hoje)
        total_hoje = vendas_hoje['Total'].sum() if not vendas_hoje.empty else 0
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                label="💵 Vendas Hoje",
                value=f"R$ {total_hoje:,.2f}",
                delta="hoje"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Alertas de estoque baixo
        if produtos_baixo:
            st.warning(f"⚠️ **Atenção:** {len(produtos_baixo)} produto(s) com estoque baixo!")
            
            with st.expander("Ver produtos com estoque baixo"):
                for produto in produtos_baixo:
                    st.markdown(f"""
                    - **{produto.nome}** 
                      - Estoque atual: {produto.estoque_atual} {produto.unidade}
                      - Estoque mínimo: {produto.estoque_minimo} {produto.unidade}
                    """)
        
        # Gráfico de vendas dos últimos 7 dias
        st.markdown("### 📈 Vendas dos Últimos 7 Dias")
        
        inicio_semana = hoje - timedelta(days=7)
        vendas_semana = RelatorioService.vendas_por_periodo(db, inicio_semana, hoje)
        
        if not vendas_semana.empty:
            import plotly.express as px
            
            fig = px.bar(
                vendas_semana,
                x='Data',
                y='Total',
                title='Evolução das Vendas',
                labels={'Total': 'Valor Total (R$)', 'Data': 'Data'},
                color='Total',
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                showlegend=False,
                height=400,
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Nenhuma venda registrada nos últimos 7 dias.")
        
        # Produtos mais vendidos
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏆 Top 5 Produtos Mais Vendidos")
            top_produtos = RelatorioService.produtos_mais_vendidos(db, inicio_mes, hoje, top=5)
            
            if not top_produtos.empty:
                import plotly.express as px
                
                fig = px.pie(
                    top_produtos,
                    values='Quantidade',
                    names='Produto',
                    title='Distribuição de Vendas'
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 Nenhum dado disponível.")
        
        with col2:
            st.markdown("### 💳 Vendas por Método de Pagamento")
            metodos = RelatorioService.vendas_por_metodo_pagamento(db, inicio_mes, hoje)
            
            if not metodos.empty:
                import plotly.express as px
                
                fig = px.bar(
                    metodos,
                    x='Método',
                    y='Total',
                    title='Faturamento por Forma de Pagamento',
                    color='Total',
                    color_continuous_scale='Greens'
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 Nenhum dado disponível.")
        
        # Informações rápidas
        st.divider()
        st.markdown("### 🎯 Acesso Rápido")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.page_link("pages/Produtos.py", label="📦 Gerenciar Produtos", use_container_width=True)
        
        with col2:
            st.page_link("pages/Vendas.py", label="🧾 Registrar Venda", use_container_width=True)
        
        with col3:
            st.page_link("pages/BI_Dashboard.py", label="📊 Ver Relatórios", use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dashboard: {str(e)}")
    
    finally:
        db.close()

# Controle de fluxo
if not st.session_state.authenticated:
    login_page()
else:
    main_page()
