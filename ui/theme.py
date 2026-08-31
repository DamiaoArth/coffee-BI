"""
Tokens de design e CSS global.

Estratégia de tema: o ERP não pinta fundo nem texto com valores fixos. As
superfícies são derivadas da cor de texto herdada com `color-mix`, de modo que
o mesmo CSS funciona no tema claro e no escuro do Streamlit sem detecção
server-side (que é pouco confiável) e sem desincronizar quando o usuário troca
o tema pelo menu.

- Texto: `inherit` (segue o `textColor` do tema ativo).
- Superfícies e bordas: `color-mix(... currentColor N% ...)` — translúcidas.
- Acentos (marca e semânticos): valores de meio-tom legíveis nos dois temas,
  com ajuste fino opcional via `prefers-color-scheme`.
"""

from __future__ import annotations

import streamlit as st

# --- acentos: meio-tom, legíveis sobre claro e escuro ----------------------
BRAND = "#8A6142"
BRAND_DARK = "#C89A6C"
POS = "#0F8A70"
NEG = "#C4362A"
WARN = "#B87514"
INFO = "#2F6FD0"

RADIUS = "10px"

# Mantido para compatibilidade com quem importa nomes antigos.
TONE_NAMES = ("neutral", "brand", "pos", "neg", "warn", "info")


def tone_colors(tone: str) -> tuple[str, str]:
    """(cor do texto, cor de fundo) do selo/pílula. Ambas adaptam ao tema."""
    mapa = {
        "neutral": ("inherit", "color-mix(in srgb, currentColor 9%, transparent)"),
        "brand": ("var(--erp-brand)", "color-mix(in srgb, var(--erp-brand) 15%, transparent)"),
        "pos": ("var(--erp-pos)", "color-mix(in srgb, var(--erp-pos) 15%, transparent)"),
        "neg": ("var(--erp-neg)", "color-mix(in srgb, var(--erp-neg) 15%, transparent)"),
        "warn": ("var(--erp-warn)", "color-mix(in srgb, var(--erp-warn) 16%, transparent)"),
        "info": ("var(--erp-info)", "color-mix(in srgb, var(--erp-info) 15%, transparent)"),
    }
    return mapa.get(tone, mapa["neutral"])


# Compatibilidade: TONES[tone] -> (fg, bg)
TONES = {t: tone_colors(t) for t in TONE_NAMES}

_CSS = f"""
<style>
.stApp {{
  --erp-brand: {BRAND};
  --erp-pos: {POS};
  --erp-neg: {NEG};
  --erp-warn: {WARN};
  --erp-info: {INFO};
  --erp-r: {RADIUS};

  /* superfícies derivadas do texto herdado: corretas em qualquer tema */
  --erp-surface: color-mix(in srgb, currentColor 4%, transparent);
  --erp-surface-2: color-mix(in srgb, currentColor 7%, transparent);
  --erp-line: color-mix(in srgb, currentColor 14%, transparent);
  --erp-line-strong: color-mix(in srgb, currentColor 26%, transparent);
  --erp-muted: color-mix(in srgb, currentColor 66%, transparent);
  --erp-faint: color-mix(in srgb, currentColor 45%, transparent);
  --erp-brand-soft: color-mix(in srgb, var(--erp-brand) 14%, transparent);
}}

@media (prefers-color-scheme: dark) {{
  .stApp {{ --erp-brand: {BRAND_DARK}; }}
}}

[data-testid="stMainBlockContainer"] {{ padding-top: 2.2rem; max-width: 1480px; }}
[data-testid="stHeader"] {{ background: transparent; }}

.stApp .erp-icon {{ display: block; flex: 0 0 auto; }}

/* ---------- cabeçalho de página ---------- */
.stApp .erp-head {{
  display: flex; align-items: center; gap: 14px;
  padding: 0 0 14px; margin: 0 0 18px;
  border-bottom: 1px solid var(--erp-line);
}}
.stApp .erp-head-mark {{
  display: grid; place-items: center;
  width: 42px; height: 42px; border-radius: var(--erp-r);
  background: var(--erp-brand-soft); color: var(--erp-brand);
  border: 1px solid color-mix(in srgb, var(--erp-brand) 30%, transparent);
}}
.stApp p.erp-head-eyebrow {{
  font-size: .68rem; font-weight: 650; letter-spacing: .11em;
  text-transform: uppercase; color: var(--erp-faint); margin: 0 0 2px;
}}
.stApp h1.erp-head-title {{
  font-size: 1.45rem; font-weight: 640; letter-spacing: -.015em;
  color: inherit; line-height: 1.2; margin: 0; padding: 0;
}}
.stApp p.erp-head-sub {{ font-size: .88rem; color: var(--erp-muted); margin: 3px 0 0; }}

/* ---------- título de seção ---------- */
.stApp .erp-section {{
  display: flex; align-items: center; gap: 9px;
  margin: 26px 0 12px; color: inherit;
}}
.stApp .erp-section > .erp-icon {{ color: var(--erp-brand); }}
.stApp .erp-section-title {{
  font-size: .74rem; font-weight: 680; letter-spacing: .1em;
  text-transform: uppercase; white-space: nowrap;
}}
.stApp .erp-section-rule {{ flex: 1 1 auto; height: 1px; background: var(--erp-line); }}
.stApp p.erp-section-caption {{
  font-size: .8rem; color: var(--erp-muted);
  margin: -6px 0 12px; max-width: 70ch;
}}

/* ---------- KPI ---------- */
.stApp .erp-kpis {{
  display: grid; gap: 12px; margin: 6px 0 4px;
  grid-template-columns: repeat(var(--n, 4), minmax(0, 1fr));
}}
@media (max-width: 1100px) {{ .stApp .erp-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
@media (max-width: 640px) {{ .stApp .erp-kpis {{ grid-template-columns: 1fr; }} }}

.stApp .erp-kpi {{
  position: relative; overflow: hidden;
  background: var(--erp-surface); border: 1px solid var(--erp-line);
  border-radius: var(--erp-r); padding: 14px 16px 15px;
}}
.stApp .erp-kpi::before {{
  content: ""; position: absolute; inset: 0 auto auto 0;
  width: 100%; height: 2px; background: var(--erp-accent, var(--erp-line-strong));
}}
.stApp .erp-kpi-top {{ display: flex; align-items: center; gap: 8px; margin-bottom: 9px; }}
.stApp .erp-kpi-top > .erp-icon {{ color: var(--erp-accent, var(--erp-faint)); }}
.stApp .erp-kpi-label {{
  font-size: .7rem; font-weight: 620; letter-spacing: .07em;
  text-transform: uppercase; color: var(--erp-muted);
}}
.stApp .erp-kpi-value {{
  font-size: 1.6rem; font-weight: 620; letter-spacing: -.02em;
  color: inherit; line-height: 1.15;
  font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1;
}}
.stApp .erp-kpi-foot {{ display: flex; align-items: center; gap: 6px; margin-top: 7px; flex-wrap: wrap; }}
.stApp .erp-kpi-delta {{
  display: inline-flex; align-items: center; gap: 4px;
  font-size: .74rem; font-weight: 600; padding: 2px 7px; border-radius: 999px;
  font-variant-numeric: tabular-nums;
}}
.stApp .erp-kpi-hint {{ font-size: .74rem; color: var(--erp-faint); }}

/* ---------- badge ---------- */
.stApp .erp-badge {{
  display: inline-flex; align-items: center; gap: 5px;
  font-size: .72rem; font-weight: 600;
  padding: 2px 9px; border-radius: 999px; white-space: nowrap;
}}

/* ---------- aviso ---------- */
.stApp .erp-notice {{
  display: flex; align-items: flex-start; gap: 10px;
  border: 1px solid; border-radius: var(--erp-r);
  padding: 11px 14px; margin: 8px 0; font-size: .87rem; line-height: 1.5;
}}
.stApp .erp-notice > .erp-icon {{ margin-top: 1px; }}
.stApp .erp-notice strong {{ font-weight: 640; }}
.stApp .erp-notice ul {{ margin: 6px 0 0 18px; padding: 0; }}

/* ---------- estado vazio ---------- */
.stApp .erp-empty {{
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  text-align: center; padding: 40px 24px;
  border: 1px dashed var(--erp-line-strong); border-radius: var(--erp-r);
  background: var(--erp-surface); color: var(--erp-muted);
}}
.stApp .erp-empty > .erp-icon {{ color: var(--erp-faint); }}
.stApp p.erp-empty-title {{ font-size: .95rem; font-weight: 620; color: inherit; margin: 0; }}
.stApp p.erp-empty-desc {{ font-size: .84rem; max-width: 46ch; margin: 0; color: var(--erp-muted); }}

/* ---------- linha de item ---------- */
.stApp .erp-row {{
  display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
  padding: 9px 0; border-bottom: 1px dashed var(--erp-line);
}}
.stApp .erp-row:last-child {{ border-bottom: 0; }}
.stApp .erp-row-name {{ font-size: .88rem; font-weight: 590; color: inherit; }}
.stApp .erp-row-meta {{ font-size: .76rem; color: var(--erp-faint); font-variant-numeric: tabular-nums; }}
.stApp .erp-row-value {{
  font-size: .88rem; font-weight: 620; color: inherit;
  font-variant-numeric: tabular-nums; white-space: nowrap;
}}

/* ---------- total ---------- */
.stApp .erp-total {{
  display: flex; align-items: baseline; justify-content: space-between;
  margin-top: 12px; padding-top: 12px;
  border-top: 2px solid color-mix(in srgb, currentColor 70%, transparent);
}}
.stApp .erp-total-label {{
  font-size: .7rem; font-weight: 660; letter-spacing: .1em;
  text-transform: uppercase; color: var(--erp-muted);
}}
.stApp .erp-total-value {{
  font-size: 1.5rem; font-weight: 660; color: inherit;
  letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}}

/* ---------- definição ---------- */
.stApp .erp-def {{ display: grid; grid-template-columns: auto 1fr; gap: 5px 16px; font-size: .87rem; }}
.stApp .erp-def dt {{ color: var(--erp-faint); white-space: nowrap; }}
.stApp .erp-def dd {{ margin: 0; color: inherit; font-weight: 560; font-variant-numeric: tabular-nums; }}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding-top: 1.4rem; }}
/* a navegação automática é substituída por `main_nav`, que carrega ícones */
[data-testid="stSidebarNav"] {{ display: none; }}

.stApp .erp-id {{
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; margin-bottom: 8px;
  border: 1px solid var(--erp-line);
  border-radius: var(--erp-r); background: var(--erp-surface);
}}
.stApp .erp-id-mark {{
  display: grid; place-items: center; width: 34px; height: 34px;
  border-radius: 8px; background: var(--erp-brand); color: #fff;
}}
.stApp .erp-id-name {{ font-size: .88rem; font-weight: 620; color: inherit; line-height: 1.2; }}
.stApp .erp-id-role {{
  font-size: .68rem; font-weight: 620; letter-spacing: .08em;
  text-transform: uppercase; color: var(--erp-faint);
}}
.stApp p.erp-navlabel {{
  font-size: .66rem; font-weight: 680; letter-spacing: .12em;
  text-transform: uppercase; color: var(--erp-faint); margin: 20px 0 6px;
}}

[data-testid="stSidebar"] [data-testid="stPageLink"] a {{
  border-radius: 8px; padding: 7px 10px; font-weight: 560; color: var(--erp-muted);
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{
  background: var(--erp-brand-soft); color: var(--erp-brand);
}}

/* ---------- widgets nativos ---------- */
[data-testid="stMetric"] {{
  background: var(--erp-surface); border: 1px solid var(--erp-line);
  border-radius: var(--erp-r); padding: 12px 14px;
}}
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}

.stApp [data-testid="stForm"] {{
  background: var(--erp-surface); border: 1px solid var(--erp-line);
  border-radius: var(--erp-r); padding: 18px 18px 8px;
}}
.stApp [data-testid="stExpander"] details {{
  background: var(--erp-surface); border: 1px solid var(--erp-line);
  border-radius: var(--erp-r);
}}
.stApp [data-testid="stDataFrame"] {{ border-radius: var(--erp-r); overflow: hidden; }}

/* ---------- tela de login: sem barra lateral ---------- */
.erp-login [data-testid="stSidebar"] {{ display: none !important; }}

/* ---------- acessibilidade ---------- */
:where(button, a, input, select, textarea):focus-visible {{
  outline: 2px solid var(--erp-brand); outline-offset: 2px;
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration: .01ms !important; transition-duration: .01ms !important; }}
}}
</style>
"""

# A tela de acesso não tem navegação: some com a barra lateral e com todos os
# controles que a reabrem (os testids variam entre versões do Streamlit).
_LOGIN_CSS = """
<style>
[data-testid="stSidebar"],
[data-testid="stSidebarContent"],
[data-testid="stSidebarHeader"],
[data-testid="stSidebarNav"],
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stHeader"] [data-testid="stExpandSidebarButton"],
button[kind="headerNoPadding"] { display: none !important; }
</style>
"""


def apply_theme(login: bool = False) -> None:
    """Injeta o CSS global. `login=True` remove a barra lateral da tela de acesso."""
    st.markdown(_CSS, unsafe_allow_html=True)
    if login:
        st.markdown(_LOGIN_CSS, unsafe_allow_html=True)


__all__ = [
    "apply_theme", "tone_colors", "TONES", "TONE_NAMES",
    "BRAND", "BRAND_DARK", "POS", "NEG", "WARN", "INFO", "RADIUS",
]
