import streamlit as st
import pandas as pd
from config.database import SessionLocal
from models.database_models import Funcionario, Usuario
from services.auth_service import AuthService
from datetime import date
import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Por favor, faça login primeiro!")
    st.stop()

# Verificar se é admin
if st.session_state.user['nivel_acesso'] != 'admin':
    st.error("❌ Acesso restrito! Apenas administradores podem acessar esta área.")
    st.stop()

st.set_page_config(page_title="Funcionários", page_icon="👥", layout="wide")

st.markdown("# 👥 Gerenciamento de Funcionários")
st.markdown("---")

with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['username']}")
    st.divider()
    
    opcao = st.radio(
        "Selecione uma opção:",
        ["📋 Listar Funcionários", "➕ Cadastrar Funcionário", "✏️ Editar Funcionário", "🔐 Gerenciar Usuários"],
        label_visibility="collapsed"
    )

db = SessionLocal()

try:
    # LISTAR FUNCIONÁRIOS
    if opcao == "📋 Listar Funcionários":
        st.markdown("## 📋 Lista de Funcionários")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            filtro_cargo = st.selectbox(
                "Filtrar por Cargo",
                ["Todos", "gerente", "barista", "caixa", "atendente", "auxiliar"]
            )
        
        with col2:
            apenas_ativos = st.checkbox("Apenas Ativos", value=True)
        
        # Buscar funcionários
        query = db.query(Funcionario)
        
        if apenas_ativos:
            query = query.filter(Funcionario.ativo == True)
        
        if filtro_cargo != "Todos":
            query = query.filter(Funcionario.cargo == filtro_cargo)
        
        funcionarios = query.order_by(Funcionario.nome).all()
        
        if funcionarios:
            st.markdown(f"**Total de funcionários:** {len(funcionarios)}")
            
            # Tabela de funcionários
            dados_funcionarios = []
            for f in funcionarios:
                # Verificar se tem usuário
                tem_usuario = "✅" if f.usuario else "❌"
                
                dados_funcionarios.append({
                    'ID': f.id,
                    'Nome': f.nome,
                    'Cargo': f.cargo,
                    'Telefone': f.telefone or '-',
                    'Email': f.email or '-',
                    'Admissão': f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-',
                    'Usuário': tem_usuario,
                    'Status': '✅ Ativo' if f.ativo else '❌ Inativo'
                })
            
            df = pd.DataFrame(dados_funcionarios)
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Estatísticas
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Funcionários", len(funcionarios))
            
            with col2:
                ativos = sum(1 for f in funcionarios if f.ativo)
                st.metric("Ativos", ativos)
            
            with col3:
                com_usuario = sum(1 for f in funcionarios if f.usuario)
                st.metric("Com Acesso Sistema", com_usuario)
            
            with col4:
                cargos = len(set(f.cargo for f in funcionarios))
                st.metric("Cargos Diferentes", cargos)
            
            # Exportar
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar Lista",
                data=csv,
                file_name="funcionarios.csv",
                mime="text/csv"
            )
        else:
            st.info("👥 Nenhum funcionário cadastrado.")
    
    # CADASTRAR FUNCIONÁRIO
    elif opcao == "➕ Cadastrar Funcionário":
        st.markdown("## ➕ Cadastrar Novo Funcionário")
        
        with st.form("form_cadastro_funcionario", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome Completo*", placeholder="Ex: João Silva")
                
                cargo = st.selectbox(
                    "Cargo*",
                    ["gerente", "barista", "caixa", "atendente", "auxiliar", "outro"]
                )
                
                telefone = st.text_input("Telefone", placeholder="(00) 00000-0000")
            
            with col2:
                email = st.text_input("E-mail", placeholder="funcionario@email.com")
                
                data_admissao = st.date_input(
                    "Data de Admissão",
                    value=date.today()
                )
                
                ativo = st.checkbox("Funcionário Ativo", value=True)
            
            st.divider()
            st.markdown("### 🔐 Criar Acesso ao Sistema (Opcional)")
            
            criar_usuario = st.checkbox("Criar usuário para acesso ao sistema")
            
            if criar_usuario:
                col1, col2 = st.columns(2)
                
                with col1:
                    nome_usuario = st.text_input("Nome de Usuário*", placeholder="joao.silva")
                
                with col2:
                    nivel_acesso = st.selectbox("Nível de Acesso*", ["caixa", "admin"])
                
                senha = st.text_input("Senha*", type="password", placeholder="Mínimo 6 caracteres")
                senha_confirm = st.text_input("Confirmar Senha*", type="password")
            
            submit = st.form_submit_button("💾 Cadastrar Funcionário", use_container_width=True, type="primary")
            
            if submit:
                if nome and cargo:
                    try:
                        # Criar funcionário
                        funcionario = Funcionario(
                            nome=nome,
                            cargo=cargo,
                            telefone=telefone if telefone else None,
                            email=email if email else None,
                            data_admissao=data_admissao,
                            ativo=ativo
                        )
                        db.add(funcionario)
                        db.flush()
                        
                        # Criar usuário se solicitado
                        if criar_usuario:
                            if nome_usuario and senha and senha == senha_confirm:
                                if len(senha) >= 6:
                                    AuthService.criar_usuario(
                                        db=db,
                                        nome_usuario=nome_usuario,
                                        senha=senha,
                                        nivel_acesso=nivel_acesso,
                                        funcionario_id=funcionario.id
                                    )
                                    st.success(f"✅ Funcionário e usuário cadastrados com sucesso!")
                                else:
                                    st.warning("⚠️ Senha deve ter no mínimo 6 caracteres!")
                                    db.rollback()
                                    st.stop()
                            else:
                                st.warning("⚠️ Preencha todos os campos do usuário ou verifique se as senhas coincidem!")
                                db.rollback()
                                st.stop()
                        else:
                            st.success(f"✅ Funcionário '{nome}' cadastrado com sucesso!")
                        
                        db.commit()
                        st.balloons()
                        
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ Erro ao cadastrar: {str(e)}")
                else:
                    st.warning("⚠️ Preencha todos os campos obrigatórios!")
    
    # EDITAR FUNCIONÁRIO
    elif opcao == "✏️ Editar Funcionário":
        st.markdown("## ✏️ Editar Funcionário")
        
        funcionarios = db.query(Funcionario).order_by(Funcionario.nome).all()
        
        if funcionarios:
            opcoes_funcionarios = {f"{f.id} - {f.nome} ({f.cargo})": f.id for f in funcionarios}
            
            funcionario_selecionado = st.selectbox(
                "Selecione o Funcionário",
                options=list(opcoes_funcionarios.keys())
            )
            
            if funcionario_selecionado:
                funcionario_id = opcoes_funcionarios[funcionario_selecionado]
                funcionario = db.query(Funcionario).filter(Funcionario.id == funcionario_id).first()
                
                if funcionario:
                    with st.form("form_edicao_funcionario"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            nome = st.text_input("Nome Completo", value=funcionario.nome)
                            cargo = st.selectbox(
                                "Cargo",
                                ["gerente", "barista", "caixa", "atendente", "auxiliar", "outro"],
                                index=["gerente", "barista", "caixa", "atendente", "auxiliar", "outro"].index(funcionario.cargo) if funcionario.cargo in ["gerente", "barista", "caixa", "atendente", "auxiliar", "outro"] else 0
                            )
                            telefone = st.text_input("Telefone", value=funcionario.telefone or "")
                        
                        with col2:
                            email = st.text_input("E-mail", value=funcionario.email or "")
                            data_admissao = st.date_input(
                                "Data de Admissão",
                                value=funcionario.data_admissao if funcionario.data_admissao else date.today()
                            )
                            ativo = st.checkbox("Funcionário Ativo", value=funcionario.ativo)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            atualizar = st.form_submit_button("💾 Atualizar", use_container_width=True, type="primary")
                        
                        with col2:
                            desativar = st.form_submit_button("🗑️ Desativar", use_container_width=True)
                        
                        if atualizar:
                            try:
                                funcionario.nome = nome
                                funcionario.cargo = cargo
                                funcionario.telefone = telefone if telefone else None
                                funcionario.email = email if email else None
                                funcionario.data_admissao = data_admissao
                                funcionario.ativo = ativo
                                
                                db.commit()
                                st.success("✅ Funcionário atualizado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ Erro ao atualizar: {str(e)}")
                        
                        if desativar:
                            funcionario.ativo = False
                            if funcionario.usuario:
                                funcionario.usuario.ativo = False
                            db.commit()
                            st.success("✅ Funcionário desativado!")
                            st.rerun()
        else:
            st.info("👥 Nenhum funcionário cadastrado.")
    
    # GERENCIAR USUÁRIOS
    elif opcao == "🔐 Gerenciar Usuários":
        st.markdown("## 🔐 Gerenciar Usuários do Sistema")
        
        usuarios = db.query(Usuario).all()
        
        if usuarios:
            st.markdown(f"**Total de usuários:** {len(usuarios)}")
            
            # Tabela de usuários
            dados_usuarios = []
            for u in usuarios:
                dados_usuarios.append({
                    'ID': u.id,
                    'Usuário': u.nome_usuario,
                    'Funcionário': u.funcionario.nome if u.funcionario else '-',
                    'Nível': u.nivel_acesso,
                    'Último Acesso': u.ultimo_acesso.strftime('%d/%m/%Y %H:%M') if u.ultimo_acesso else 'Nunca',
                    'Status': '✅ Ativo' if u.ativo else '❌ Inativo'
                })
            
            df_usuarios = pd.DataFrame(dados_usuarios)
            
            st.dataframe(
                df_usuarios,
                use_container_width=True,
                hide_index=True,
                height=300
            )
            
            st.divider()
            
            # Criar novo usuário
            st.markdown("### ➕ Criar Novo Usuário")
            
            with st.form("form_novo_usuario"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    novo_username = st.text_input("Nome de Usuário*")
                
                with col2:
                    nova_senha = st.text_input("Senha*", type="password")
                
                with col3:
                    novo_nivel = st.selectbox("Nível*", ["caixa", "admin"])
                
                # Selecionar funcionário (opcional)
                funcionarios = db.query(Funcionario).filter(Funcionario.ativo == True).all()
                funcionarios_sem_usuario = [f for f in funcionarios if not f.usuario]
                
                if funcionarios_sem_usuario:
                    opcoes_func = {f"Nenhum": None}
                    opcoes_func.update({f.nome: f.id for f in funcionarios_sem_usuario})
                    
                    func_selecionado = st.selectbox(
                        "Vincular a Funcionário (Opcional)",
                        options=list(opcoes_func.keys())
                    )
                    funcionario_id_selecionado = opcoes_func[func_selecionado]
                else:
                    st.info("ℹ️ Todos os funcionários já possuem usuário.")
                    funcionario_id_selecionado = None
                
                criar = st.form_submit_button("➕ Criar Usuário", use_container_width=True, type="primary")
                
                if criar:
                    if novo_username and nova_senha:
                        if len(nova_senha) >= 6:
                            try:
                                # Verificar se usuário já existe
                                existe = db.query(Usuario).filter(Usuario.nome_usuario == novo_username).first()
                                if existe:
                                    st.error("❌ Nome de usuário já existe!")
                                else:
                                    AuthService.criar_usuario(
                                        db=db,
                                        nome_usuario=novo_username,
                                        senha=nova_senha,
                                        nivel_acesso=novo_nivel,
                                        funcionario_id=funcionario_id_selecionado
                                    )
                                    st.success(f"✅ Usuário '{novo_username}' criado com sucesso!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao criar usuário: {str(e)}")
                        else:
                            st.warning("⚠️ Senha deve ter no mínimo 6 caracteres!")
                    else:
                        st.warning("⚠️ Preencha todos os campos obrigatórios!")
            
            # Redefinir senha
            st.divider()
            st.markdown("### 🔑 Redefinir Senha de Usuário")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                usuario_resetar = st.selectbox(
                    "Selecionar Usuário",
                    options=[u.nome_usuario for u in usuarios]
                )
            
            with col2:
                nova_senha_reset = st.text_input("Nova Senha", type="password", key="reset_senha")
            
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔑 Redefinir", use_container_width=True):
                    if nova_senha_reset and len(nova_senha_reset) >= 6:
                        usuario = db.query(Usuario).filter(Usuario.nome_usuario == usuario_resetar).first()
                        if usuario:
                            usuario.senha_hash = AuthService.hash_password(nova_senha_reset)
                            db.commit()
                            st.success(f"✅ Senha de '{usuario_resetar}' redefinida!")
                    else:
                        st.warning("⚠️ Senha deve ter no mínimo 6 caracteres!")
        else:
            st.info("🔐 Nenhum usuário cadastrado.")

finally:
    db.close()