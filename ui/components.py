"""Componentes de UI reutilizáveis do ERP."""

from __future__ import annotations

from html import escape
from typing import Iterable, Sequence

import streamlit as st

from ui.icons import icon, material
from ui.theme import tone_colors

_ACCENT = {
    "neutral": "var(--erp-line-strong)",
    "brand": "var(--erp-brand)",
    "pos": "var(--erp-pos)",
    "neg": "var(--erp-neg)",
    "warn": "var(--erp-warn)",
    "info": "var(--erp-info)",
}


def _esc(value) -> str:
    return escape(str(value), quote=False)


# --------------------------------------------------------------------------- #
# Cabeçalhos
# --------------------------------------------------------------------------- #
def page_header(
    icon_name: str,
    title: str,
    subtitle: str | None = None,
    eyebrow: str = "ERP Cafeteria",
) -> None:
    sub = f'<p class="erp-head-sub">{_esc(subtitle)}</p>' if subtitle else ""
    st.markdown(
        f'<header class="erp-head">'
        f'  <div class="erp-head-mark">{icon(icon_name, 22)}</div>'
        f"  <div>"
        f'    <p class="erp-head-eyebrow">{_esc(eyebrow)}</p>'
        f'    <h1 class="erp-head-title">{_esc(title)}</h1>{sub}'
        f"  </div>"
        f"</header>",
        unsafe_allow_html=True,
    )


def section(icon_name: str, title: str, caption: str | None = None) -> None:
    st.markdown(
        f'<div class="erp-section">{icon(icon_name, 17)}'
        f'<span class="erp-section-title">{_esc(title)}</span>'
        f'<span class="erp-section-rule"></span></div>',
        unsafe_allow_html=True,
    )
    if caption:
        st.markdown(
            f'<p class="erp-section-caption">{_esc(caption)}</p>',
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Indicadores
# --------------------------------------------------------------------------- #
def kpi_card(
    label: str,
    value: str,
    icon_name: str,
    delta: str | None = None,
    delta_tone: str = "neutral",
    hint: str | None = None,
    tone: str = "neutral",
) -> str:
    """Retorna o HTML de um card de indicador (use via `kpi_row`)."""
    foot = ""
    if delta:
        fg, bg = tone_colors(delta_tone)
        foot += (
            f'<span class="erp-kpi-delta" style="color:{fg};background:{bg};">'
            f"{_esc(delta)}</span>"
        )
    if hint:
        foot += f'<span class="erp-kpi-hint">{_esc(hint)}</span>'
    if foot:
        foot = f'<div class="erp-kpi-foot">{foot}</div>'

    return (
        f'<article class="erp-kpi" style="--erp-accent:{_ACCENT.get(tone, _ACCENT["neutral"])};">'
        f'  <div class="erp-kpi-top">{icon(icon_name, 16)}'
        f'    <span class="erp-kpi-label">{_esc(label)}</span></div>'
        f'  <div class="erp-kpi-value">{_esc(value)}</div>{foot}'
        f"</article>"
    )


def kpi_row(cards: Sequence[str]) -> None:
    """Renderiza cards de KPI em grade responsiva."""
    if not cards:
        return
    st.markdown(
        f'<div class="erp-kpis" style="--n:{len(cards)};">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Sinalização
# --------------------------------------------------------------------------- #
_NOTICE = {
    "info": ("info", "info"),
    "success": ("check_circle", "pos"),
    "warning": ("alert", "warn"),
    "error": ("x_circle", "neg"),
}


def notice(text: str, kind: str = "info", icon_name: str | None = None) -> None:
    default_icon, tone = _NOTICE.get(kind, _NOTICE["info"])
    fg, bg = tone_colors(tone)
    borda = (
        "var(--erp-line-strong)"
        if tone == "neutral"
        else f"color-mix(in srgb, {fg} 34%, transparent)"
    )
    st.markdown(
        f'<div class="erp-notice" style="color:{fg};background:{bg};border-color:{borda};">'
        f"{icon(icon_name or default_icon, 17)}<div>{text}</div></div>",
        unsafe_allow_html=True,
    )


def badge(text: str, tone: str = "neutral", icon_name: str | None = None) -> str:
    """Retorna o HTML de um selo. Uso inline dentro de outro markdown."""
    fg, bg = tone_colors(tone)
    ico = icon(icon_name, 13) if icon_name else ""
    return (
        f'<span class="erp-badge" style="color:{fg};background:{bg};">'
        f"{ico}{_esc(text)}</span>"
    )


def empty_state(
    icon_name: str, title: str, description: str | None = None
) -> None:
    desc = f'<p class="erp-empty-desc">{_esc(description)}</p>' if description else ""
    st.markdown(
        f'<div class="erp-empty">{icon(icon_name, 30)}'
        f'<p class="erp-empty-title">{_esc(title)}</p>{desc}</div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Blocos de conteúdo
# --------------------------------------------------------------------------- #
def definition_list(pairs: Iterable[tuple[str, str]]) -> None:
    body = "".join(
        f"<dt>{_esc(k)}</dt><dd>{_esc(v)}</dd>" for k, v in pairs
    )
    st.markdown(f'<dl class="erp-def">{body}</dl>', unsafe_allow_html=True)


def line_item(name: str, meta: str, value: str) -> None:
    st.markdown(
        f'<div class="erp-row"><div><div class="erp-row-name">{_esc(name)}</div>'
        f'<div class="erp-row-meta">{_esc(meta)}</div></div>'
        f'<div class="erp-row-value">{_esc(value)}</div></div>',
        unsafe_allow_html=True,
    )


def total_line(label: str, value: str) -> None:
    st.markdown(
        f'<div class="erp-total"><span class="erp-total-label">{_esc(label)}</span>'
        f'<span class="erp-total-value">{_esc(value)}</span></div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def sidebar_identity(username: str, role: str) -> None:
    st.markdown(
        f'<div class="erp-id"><div class="erp-id-mark">{icon("user", 18)}</div>'
        f'<div><div class="erp-id-name">{_esc(username)}</div>'
        f'<div class="erp-id-role">{_esc(role)}</div></div></div>',
        unsafe_allow_html=True,
    )


PAGINAS = [
    ("app.py", "Visão geral", "dashboard", False),
    ("pages/Vendas.py", "Vendas", "cart", False),
    ("pages/Produtos.py", "Produtos", "box", False),
    ("pages/Compras.py", "Compras", "truck", False),
    ("pages/Financeiro.py", "Financeiro", "wallet", True),
    ("pages/Funcionarios.py", "Equipe", "users", True),
    ("pages/BI_Dashboard.py", "Business Intelligence", "analytics", False),
]


def main_nav(pode_gerir: bool) -> None:
    """Navegação principal com ícones. Oculta as áreas sem permissão."""
    st.markdown('<p class="erp-navlabel">Navegação</p>', unsafe_allow_html=True)
    for caminho, texto, icon_name, restrita in PAGINAS:
        if restrita and not pode_gerir:
            continue
        st.page_link(caminho, label=texto, icon=material(icon_name), width="stretch")


def sidebar_nav(
    items: Sequence[tuple[str, str, str]],
    state_key: str,
    title: str = "Seções",
) -> str:
    """
    Navegação lateral com ícones.

    items: sequência de (valor, rótulo, nome_do_ícone).
    Retorna o valor selecionado, persistido em `st.session_state[state_key]`.
    """
    values = [value for value, _, _ in items]
    if st.session_state.get(state_key) not in values:
        st.session_state[state_key] = values[0]

    st.markdown(f'<p class="erp-navlabel">{_esc(title)}</p>', unsafe_allow_html=True)
    for value, text, icon_name in items:
        active = st.session_state[state_key] == value
        if st.button(
            text,
            key=f"{state_key}__{value}",
            icon=material(icon_name),
            width="stretch",
            type="primary" if active else "secondary",
        ):
            st.session_state[state_key] = value
            st.rerun()

    return st.session_state[state_key]


# --------------------------------------------------------------------------- #
# Dados
# --------------------------------------------------------------------------- #
def data_table(df, height: int | None = None, **kwargs) -> None:
    if height is not None:
        kwargs["height"] = height
    st.dataframe(df, width="stretch", hide_index=True, **kwargs)


def download_csv(df, filename: str, label: str = "Exportar CSV", key: str | None = None) -> None:
    st.download_button(
        label,
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        icon=material("download"),
        width="stretch",
        key=key,
    )


__all__ = [
    "page_header", "section", "kpi_card", "kpi_row", "notice", "badge",
    "empty_state", "definition_list", "line_item", "total_line",
    "sidebar_identity", "sidebar_nav", "main_nav", "PAGINAS",
    "data_table", "download_csv",
]
