"""Refresh legacy Streamlit authorization on each rerun."""

import streamlit as st

from config.database import SessionLocal
from models.database_models import Usuario


def require_login():
    state = st.session_state.get("user")
    if not st.session_state.get("authenticated") or not state:
        st.warning("Faça login para continuar.")
        st.stop()
    with SessionLocal() as db:
        user = db.get(Usuario, state.get("id"))
        if (
            not user
            or not user.ativo
            or (user.funcionario and not user.funcionario.ativo)
        ):
            st.session_state.clear()
            st.warning("Acesso desativado. Faça login novamente.")
            st.stop()
        st.session_state.user = {
            "id": user.id,
            "username": user.nome_usuario,
            "nivel_acesso": user.nivel_acesso,
            "funcionario_id": user.funcionario_id,
        }
