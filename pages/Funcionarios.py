import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.page import ROLES_GESTAO, role_label, setup_page  # noqa: E402

user = setup_page(
    title="Funcionários",
    icon_name="users",
    heading="Equipe e acessos",
    subtitle="Cadastro da equipe, vínculos e contas de acesso ao sistema.",
    roles=ROLES_GESTAO,
)

from config.database import SessionLocal  # noqa: E402
from models.database_models import Funcionario, Usuario  # noqa: E402
from services.auth_service import AuthService  # noqa: E402
from ui.components import (  # noqa: E402
    badge,
    data_table,
    download_csv,
    empty_state,
    kpi_card,
    kpi_row,
    notice,
    section,
    sidebar_nav,
)
from ui.format import data_br, num  # noqa: E402
from ui.icons import material  # noqa: E402

CARGOS = ["admin", "Gerente", "funcionario"]
SENHA_MINIMA = 6

with st.sidebar:
    opcao = sidebar_nav(
        [
            ("equipe", "Equipe", "list"),
            ("novo", "Cadastrar", "user_plus"),
            ("editar", "Editar", "edit"),
            ("acessos", "Acessos", "key"),
        ],
        state_key="nav_funcionarios",
    )

db = SessionLocal()

try:
    # -------------------------------------------------------------------- equipe
    if opcao == "equipe":
        section("filter", "Filtros")
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            f_cargo = st.selectbox(
                "Cargo", ["Todos"] + CARGOS, format_func=lambda c: c if c == "Todos" else role_label(c)
            )
        with c2:
            apenas_ativos = st.checkbox("Somente ativos", value=True)

        query = db.query(Funcionario)
        if apenas_ativos:
            query = query.filter(Funcionario.ativo.is_(True))
        if f_cargo != "Todos":
            query = query.filter(Funcionario.cargo == f_cargo)
        funcionarios = query.order_by(Funcionario.nome).all()

        if not funcionarios:
            empty_state(
                "users",
                "Nenhum funcionário",
                "Cadastre a equipe para vincular vendas e acessos.",
            )
        else:
            com_acesso = sum(1 for f in funcionarios if f.usuario)
            ativos = sum(1 for f in funcionarios if f.ativo)

            kpi_row(
                [
                    kpi_card("Equipe", num(len(funcionarios)), "users", tone="brand"),
                    kpi_card("Ativos", num(ativos), "check_circle", tone="pos"),
                    kpi_card("Com acesso", num(com_acesso), "key",
                             hint="contas no sistema"),
                    kpi_card("Cargos", num(len({f.cargo for f in funcionarios})), "shield"),
                ]
            )

            section("list", "Equipe")
            df = pd.DataFrame(
                [
                    {
                        "Nº": f.id,
                        "Nome": f.nome,
                        "Cargo": role_label(f.cargo),
                        "Telefone": f.telefone or "—",
                        "E-mail": f.email or "—",
                        "Admissão": data_br(f.data_admissao),
                        "Acesso": "Sim" if f.usuario else "Não",
                        "Situação": "Ativo" if f.ativo else "Inativo",
                    }
                    for f in funcionarios
                ]
            )
            data_table(df, height=400)

            c_export, _ = st.columns([1, 3])
            with c_export:
                download_csv(df, "funcionarios.csv", "Exportar equipe")

    # ----------------------------------------------------------------- cadastrar
    elif opcao == "novo":
        section("user_plus", "Novo funcionário")

        with st.form("cadastro_funcionario", clear_on_submit=True):
            c1, c2 = st.columns(2, gap="large")
            with c1:
                nome = st.text_input("Nome completo*", placeholder="Ex.: Ana Souza")
                cargo = st.selectbox("Cargo*", CARGOS, format_func=role_label)
                telefone = st.text_input("Telefone", placeholder="(00) 00000-0000")
            with c2:
                email = st.text_input("E-mail", placeholder="nome@cafeteria.com.br")
                data_admissao = st.date_input(
                    "Data de admissão", value=date.today(), format="DD/MM/YYYY"
                )
                ativo = st.checkbox("Funcionário ativo", value=True)

            st.divider()
            criar_acesso = st.checkbox("Criar conta de acesso ao sistema")
            c3, c4 = st.columns(2, gap="large")
            with c3:
                nome_usuario = st.text_input("Nome de usuário", placeholder="ana.souza")
                senha = st.text_input(
                    "Senha", type="password", placeholder=f"Mínimo {SENHA_MINIMA} caracteres"
                )
            with c4:
                nivel = st.selectbox(
                    "Nível de acesso", CARGOS, format_func=role_label, key="nivel_novo"
                )
                senha_confirma = st.text_input("Confirmar senha", type="password")

            salvar = st.form_submit_button(
                "Cadastrar funcionário",
                width="stretch",
                type="primary",
                icon=material("save"),
            )

        if salvar:
            erro_validacao = None
            if not nome.strip():
                erro_validacao = "Informe o nome completo."
            elif criar_acesso:
                if not nome_usuario.strip() or not senha:
                    erro_validacao = "Preencha usuário e senha da conta de acesso."
                elif senha != senha_confirma:
                    erro_validacao = "As senhas não coincidem."
                elif len(senha) < SENHA_MINIMA:
                    erro_validacao = f"A senha precisa de ao menos {SENHA_MINIMA} caracteres."
                elif (
                    db.query(Usuario)
                    .filter(Usuario.nome_usuario == nome_usuario.strip())
                    .first()
                ):
                    erro_validacao = "Esse nome de usuário já existe."

            if erro_validacao:
                notice(erro_validacao, "warning")
            else:
                try:
                    funcionario = Funcionario(
                        nome=nome.strip(),
                        cargo=cargo,
                        telefone=telefone.strip() or None,
                        email=email.strip() or None,
                        data_admissao=data_admissao,
                        ativo=ativo,
                    )
                    db.add(funcionario)
                    db.flush()

                    if criar_acesso:
                        AuthService.criar_usuario(
                            db=db,
                            nome_usuario=nome_usuario.strip(),
                            senha=senha,
                            nivel_acesso=nivel,
                            funcionario_id=funcionario.id,
                        )

                    db.commit()
                    st.toast(f"{funcionario.nome} cadastrado.", icon=material("check"))
                except Exception as erro:
                    db.rollback()
                    notice(f"Não foi possível cadastrar: {erro}", "error")

    # -------------------------------------------------------------------- editar
    elif opcao == "editar":
        funcionarios = db.query(Funcionario).order_by(Funcionario.nome).all()

        if not funcionarios:
            empty_state("users", "Nada para editar", "Cadastre um funcionário primeiro.")
        else:
            section("edit", "Editar funcionário")
            mapa = {f"{f.id} · {f.nome} · {role_label(f.cargo)}": f.id for f in funcionarios}
            escolhido = st.selectbox("Funcionário", options=list(mapa.keys()))
            funcionario = (
                db.query(Funcionario).filter(Funcionario.id == mapa[escolhido]).first()
            )

            if funcionario:
                st.markdown(
                    badge("Ativo" if funcionario.ativo else "Inativo",
                          "pos" if funcionario.ativo else "neutral", "check")
                    + " "
                    + badge(role_label(funcionario.cargo), "brand", "shield")
                    + " "
                    + badge(
                        "Com acesso" if funcionario.usuario else "Sem acesso",
                        "info" if funcionario.usuario else "neutral",
                        "key",
                    ),
                    unsafe_allow_html=True,
                )

                with st.form("edicao_funcionario"):
                    c1, c2 = st.columns(2, gap="large")
                    with c1:
                        nome = st.text_input("Nome completo", value=funcionario.nome)
                        cargo = st.selectbox(
                            "Cargo",
                            CARGOS,
                            index=CARGOS.index(funcionario.cargo)
                            if funcionario.cargo in CARGOS
                            else 0,
                            format_func=role_label,
                        )
                        telefone = st.text_input("Telefone", value=funcionario.telefone or "")
                    with c2:
                        email = st.text_input("E-mail", value=funcionario.email or "")
                        data_admissao = st.date_input(
                            "Data de admissão",
                            value=funcionario.data_admissao or date.today(),
                            format="DD/MM/YYYY",
                        )
                        ativo = st.checkbox("Funcionário ativo", value=funcionario.ativo)

                    c_ok, c_off = st.columns(2)
                    with c_ok:
                        atualizar = st.form_submit_button(
                            "Salvar alterações",
                            width="stretch",
                            type="primary",
                            icon=material("save"),
                        )
                    with c_off:
                        desligar = st.form_submit_button(
                            "Desativar e revogar acesso",
                            width="stretch",
                            icon=material("x_circle"),
                        )

                if atualizar:
                    try:
                        funcionario.nome = nome.strip()
                        funcionario.cargo = cargo
                        funcionario.telefone = telefone.strip() or None
                        funcionario.email = email.strip() or None
                        funcionario.data_admissao = data_admissao
                        funcionario.ativo = ativo
                        db.commit()
                        st.toast("Alterações salvas.", icon=material("check"))
                        st.rerun()
                    except Exception as erro:
                        db.rollback()
                        notice(f"Não foi possível salvar: {erro}", "error")

                if desligar:
                    funcionario.ativo = False
                    if funcionario.usuario:
                        funcionario.usuario.ativo = False
                    db.commit()
                    st.toast(f"{funcionario.nome} desativado.", icon=material("check"))
                    st.rerun()

    # ------------------------------------------------------------------- acessos
    else:
        usuarios = db.query(Usuario).order_by(Usuario.nome_usuario).all()

        if usuarios:
            ativos = sum(1 for u in usuarios if u.ativo)
            nunca_acessaram = sum(1 for u in usuarios if not u.ultimo_acesso)

            kpi_row(
                [
                    kpi_card("Contas", num(len(usuarios)), "key", tone="brand"),
                    kpi_card("Ativas", num(ativos), "check_circle", tone="pos"),
                    kpi_card(
                        "Nunca acessaram",
                        num(nunca_acessaram),
                        "clock",
                        tone="warn" if nunca_acessaram else "neutral",
                    ),
                    kpi_card(
                        "Administradores",
                        num(sum(1 for u in usuarios if u.nivel_acesso == "admin")),
                        "shield",
                    ),
                ]
            )

            section("key", "Contas de acesso")
            data_table(
                pd.DataFrame(
                    [
                        {
                            "Nº": u.id,
                            "Usuário": u.nome_usuario,
                            "Funcionário": u.funcionario.nome if u.funcionario else "—",
                            "Nível": role_label(u.nivel_acesso),
                            "Último acesso": (
                                u.ultimo_acesso.strftime("%d/%m/%Y %H:%M")
                                if u.ultimo_acesso
                                else "Nunca"
                            ),
                            "Situação": "Ativa" if u.ativo else "Inativa",
                        }
                        for u in usuarios
                    ]
                ),
                height=300,
            )
        else:
            empty_state("key", "Nenhuma conta criada", "Crie a primeira conta abaixo.")

        section("user_plus", "Criar conta")
        sem_conta = [
            f
            for f in db.query(Funcionario).filter(Funcionario.ativo.is_(True)).all()
            if not f.usuario
        ]

        with st.form("nova_conta"):
            c1, c2, c3 = st.columns(3, gap="large")
            with c1:
                novo_usuario = st.text_input("Nome de usuário*")
            with c2:
                nova_senha = st.text_input(
                    "Senha*", type="password", placeholder=f"Mínimo {SENHA_MINIMA} caracteres"
                )
            with c3:
                novo_nivel = st.selectbox("Nível*", CARGOS, format_func=role_label)

            vinculo = {"Nenhum": None}
            vinculo.update({f.nome: f.id for f in sem_conta})
            escolha_vinculo = st.selectbox(
                "Vincular a um funcionário", options=list(vinculo.keys())
            )
            if not sem_conta:
                st.caption("Todos os funcionários ativos já possuem conta.")

            criar = st.form_submit_button(
                "Criar conta",
                width="stretch",
                type="primary",
                icon=material("user_plus"),
            )

        if criar:
            if not novo_usuario.strip() or not nova_senha:
                notice("Preencha usuário e senha.", "warning")
            elif len(nova_senha) < SENHA_MINIMA:
                notice(f"A senha precisa de ao menos {SENHA_MINIMA} caracteres.", "warning")
            elif (
                db.query(Usuario)
                .filter(Usuario.nome_usuario == novo_usuario.strip())
                .first()
            ):
                notice("Esse nome de usuário já existe.", "warning")
            else:
                try:
                    AuthService.criar_usuario(
                        db=db,
                        nome_usuario=novo_usuario.strip(),
                        senha=nova_senha,
                        nivel_acesso=novo_nivel,
                        funcionario_id=vinculo[escolha_vinculo],
                    )
                    st.toast(f"Conta {novo_usuario.strip()} criada.", icon=material("check"))
                    st.rerun()
                except Exception as erro:
                    notice(f"Não foi possível criar a conta: {erro}", "error")

        if usuarios:
            section("refresh", "Redefinir senha")
            c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
            with c1:
                alvo = st.selectbox("Conta", options=[u.nome_usuario for u in usuarios])
            with c2:
                senha_nova = st.text_input(
                    "Nova senha", type="password", key="reset_senha"
                )
            with c3:
                redefinir = st.button(
                    "Redefinir", width="stretch", icon=material("key")
                )

            if redefinir:
                if len(senha_nova) < SENHA_MINIMA:
                    notice(
                        f"A senha precisa de ao menos {SENHA_MINIMA} caracteres.", "warning"
                    )
                else:
                    conta = (
                        db.query(Usuario).filter(Usuario.nome_usuario == alvo).first()
                    )
                    if conta:
                        conta.senha_hash = AuthService.hash_password(senha_nova)
                        db.commit()
                        st.toast(f"Senha de {alvo} redefinida.", icon=material("check"))
                    else:
                        notice("Conta não encontrada.", "error")

finally:
    db.close()
