"""
Bootstrap de página.

`setup_page` garante a ordem correta: `st.set_page_config` é sempre a primeira
chamada Streamlit do script, depois o tema, depois o controle de acesso.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components import (  # noqa: E402
    empty_state,
    main_nav,
    notice,
    page_header,
    sidebar_identity,
)
from ui.icons import material  # noqa: E402
from ui.theme import apply_theme  # noqa: E402

ROLES_GESTAO = {"admin", "Gerente"}

_ROLE_LABEL = {
    "admin": "Administrador",
    "Gerente": "Gerente",
    "funcionario": "Funcionário",
}


def role_label(role: str) -> str:
    return _ROLE_LABEL.get(role, role.capitalize())


def logout() -> None:
    st.session_state.authenticated = False
    st.session_state.user = None
    st.switch_page("app.py")


def sidebar_shell(user: dict) -> None:
    """Identidade, saída e navegação principal. Comum a todas as páginas."""
    with st.sidebar:
        sidebar_identity(user["username"], role_label(user.get("nivel_acesso", "")))
        if st.button(
            "Sair da conta",
            key="sair",
            width="stretch",
            icon=material("logout"),
        ):
            logout()
        main_nav(user.get("nivel_acesso") in ROLES_GESTAO)


def setup_page(
    title: str,
    icon_name: str,
    heading: str,
    subtitle: str | None = None,
    roles: Iterable[str] | None = None,
) -> dict:
    """
    Configura a página, aplica o tema, valida a sessão e desenha o cabeçalho.

    Interrompe o script (`st.stop`) se o acesso não for permitido.
    Retorna os dados do usuário autenticado.
    """
    st.set_page_config(
        page_title=f"{title} · ERP Cafeteria",
        page_icon=material(icon_name),
        layout="wide",
        initial_sidebar_state="expanded",
    )
    autenticado = bool(st.session_state.get("authenticated"))
    apply_theme(login=not autenticado)

    user = st.session_state.get("user")
    if not autenticado or not user or "username" not in user:
        empty_state(
            "lock",
            "Sessão não iniciada",
            "Entre pela página inicial para acessar esta área.",
        )
        st.page_link("app.py", label="Ir para o login", icon=material("login"))
        st.stop()

    if roles is not None and user.get("nivel_acesso") not in set(roles):
        empty_state(
            "shield",
            "Acesso restrito",
            "Esta área é limitada a administradores e gerentes. "
            "Fale com um administrador se precisar de permissão.",
        )
        st.stop()

    page_header(icon_name, heading, subtitle)
    sidebar_shell(user)

    return user


__all__ = [
    "setup_page", "sidebar_shell", "logout", "role_label",
    "ROLES_GESTAO", "ROOT", "notice",
]
