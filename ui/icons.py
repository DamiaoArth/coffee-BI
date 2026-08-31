"""
Registry central de ícones.

Cada ícone tem duas representações a partir de uma única fonte de verdade:

- `svg(...)`      -> SVG inline (usado em superfícies HTML: headers, KPIs, badges).
- `material`      -> string ":material/nome:" para os widgets nativos do Streamlit
                     (st.button, st.page_link, st.expander, st.download_button...).

Traçado uniforme: viewBox 24x24, stroke currentColor, linecap/linejoin round.
Nenhuma dependência de fonte externa ou rede.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

_SVG_TPL = (
    '<svg class="erp-icon" width="{size}" height="{size}" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="{sw}" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
    'focusable="false" role="img">{body}</svg>'
)


@dataclass(frozen=True)
class Icon:
    name: str
    body: str
    material: str

    def svg(self, size: int = 20, stroke: float = 1.7) -> str:
        return _SVG_TPL.format(size=size, sw=stroke, body=self.body)

    def __str__(self) -> str:  # permite usar o ícone direto em f-strings
        return self.svg()


_PATHS: dict[str, tuple[str, str]] = {
    # --- marca / identidade -------------------------------------------------
    "coffee": (
        '<path d="M4 8.5h11v5.8a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z"/>'
        '<path d="M15 9.8h2.4a2.4 2.4 0 0 1 0 4.8H15"/>'
        '<path d="M6.6 3v2.2M9.6 3v2.2M12.6 3v2.2"/>'
        '<path d="M3.5 21h13"/>',
        "coffee",
    ),
    "storefront": (
        '<path d="M4.5 10.2V19.5h15v-9.3"/>'
        '<path d="M2.5 10.2 4.6 4.5h14.8l2.1 5.7z"/>'
        '<path d="M9.6 19.5v-5.3h4.8v5.3"/>',
        "storefront",
    ),
    # --- acesso -------------------------------------------------------------
    "lock": (
        '<rect x="4.2" y="10.2" width="15.6" height="9.6" rx="2.2"/>'
        '<path d="M8.2 10.2V7.4a3.8 3.8 0 0 1 7.6 0v2.8"/>',
        "lock",
    ),
    "key": (
        '<circle cx="7.8" cy="12" r="3.8"/><path d="M11.6 12h9"/>'
        '<path d="M18 12v3.2M15 12v2.2"/>',
        "key",
    ),
    "shield": (
        '<path d="M12 3.4 4.6 6.3v6.1c0 4.3 3 7.4 7.4 8.8 4.4-1.4 7.4-4.5 7.4-8.8V6.3z"/>'
        '<path d="m9.2 12.2 2.1 2.1 3.9-4.2"/>',
        "shield_person",
    ),
    "logout": (
        '<path d="M14.6 4.5h3.2a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-3.2"/>'
        '<path d="m9.4 8.2-3.8 3.8 3.8 3.8"/><path d="M5.6 12h9.4"/>',
        "logout",
    ),
    "login": (
        '<path d="M9.4 4.5H6.2a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h3.2"/>'
        '<path d="m14.6 8.2 3.8 3.8-3.8 3.8"/><path d="M18.4 12H9"/>',
        "login",
    ),
    "user": (
        '<circle cx="12" cy="8.2" r="3.5"/><path d="M4.8 20a7.2 7.2 0 0 1 14.4 0"/>',
        "person",
    ),
    "users": (
        '<circle cx="9.2" cy="8.2" r="3.3"/><path d="M2.8 20a6.4 6.4 0 0 1 12.8 0"/>'
        '<path d="M16.2 5.4a3.2 3.2 0 0 1 0 5.6"/>'
        '<path d="M17.6 14.3A6.5 6.5 0 0 1 21.4 20"/>',
        "groups",
    ),
    "user_plus": (
        '<circle cx="9.4" cy="8.2" r="3.4"/><path d="M3 20a6.5 6.5 0 0 1 12.8 0"/>'
        '<path d="M18.6 8.4v5M21.1 10.9h-5"/>',
        "person_add",
    ),
    # --- navegação principal -----------------------------------------------
    "dashboard": (
        '<rect x="3.6" y="3.6" width="7" height="7" rx="1.6"/>'
        '<rect x="13.4" y="3.6" width="7" height="7" rx="1.6"/>'
        '<rect x="3.6" y="13.4" width="7" height="7" rx="1.6"/>'
        '<rect x="13.4" y="13.4" width="7" height="7" rx="1.6"/>',
        "dashboard",
    ),
    "box": (
        '<path d="M20.4 7.6 12 3.2 3.6 7.6v8.8L12 20.8l8.4-4.4z"/>'
        '<path d="M3.8 7.7 12 12l8.2-4.3"/><path d="M12 12v8.8"/>',
        "inventory_2",
    ),
    "cart": (
        '<circle cx="9.6" cy="19.4" r="1.5"/><circle cx="17.4" cy="19.4" r="1.5"/>'
        '<path d="M2.6 3.6h2.3l2.3 11.1a1.7 1.7 0 0 0 1.7 1.3h8.5a1.7 1.7 0 0 0 1.6-1.3'
        'l1.5-7.1H6.1"/>',
        "shopping_cart",
    ),
    "truck": (
        '<path d="M2.6 6.4h10.6v9.4H2.6z"/>'
        '<path d="M13.2 9.6h3.6l2.9 3.1v3.1h-6.5z"/>'
        '<circle cx="7" cy="18" r="1.7"/><circle cx="17" cy="18" r="1.7"/>',
        "local_shipping",
    ),
    "wallet": (
        '<rect x="3.4" y="6.2" width="17.2" height="12.4" rx="2.2"/>'
        '<path d="M3.4 9.6h12"/>'
        '<path d="M20.6 11.8h-3.2a2.1 2.1 0 0 0 0 4.2h3.2"/>',
        "account_balance_wallet",
    ),
    "analytics": (
        '<path d="M3.6 3.6v16.8h16.8"/>'
        '<path d="M7.4 20.4v-6.2M12 20.4V8.6M16.6 20.4v-3.8"/>',
        "analytics",
    ),
    # --- dados / gráficos ---------------------------------------------------
    "bar_chart": (
        '<path d="M3.4 20.6h17.2"/>'
        '<path d="M6.8 20.6v-6M12 20.6V7.6M17.2 20.6v-9"/>',
        "bar_chart",
    ),
    "line_chart": (
        '<path d="M3.6 3.6v16.8h16.8"/><path d="m7 15.6 3.6-4.2 3 2.6 4.6-6.2"/>',
        "show_chart",
    ),
    "pie_chart": (
        '<path d="M12 3.6V12h8.4A8.4 8.4 0 0 0 12 3.6z"/>'
        '<path d="M20.1 15.2A8.4 8.4 0 1 1 9.6 3.9"/>',
        "pie_chart",
    ),
    "layers": (
        '<path d="m12 3.4 8.4 4.3-8.4 4.3-8.4-4.3z"/>'
        '<path d="m3.6 12.4 8.4 4.3 8.4-4.3"/>'
        '<path d="m3.6 16.6 8.4 4.3 8.4-4.3"/>',
        "layers",
    ),
    "trending_up": (
        '<path d="m3.6 16.8 5.8-5.8 3.4 3.4 6.8-6.8"/>'
        '<path d="M15.2 7.2h4.8V12"/>',
        "trending_up",
    ),
    "trending_down": (
        '<path d="m3.6 7.2 5.8 5.8 3.4-3.4 6.8 6.8"/>'
        '<path d="M15.2 16.8h4.8V12"/>',
        "trending_down",
    ),
    "target": (
        '<circle cx="12" cy="12" r="8.4"/><circle cx="12" cy="12" r="4.6"/>'
        '<circle cx="12" cy="12" r="1"/>',
        "target",
    ),
    "percent": (
        '<path d="m6.4 17.6 11.2-11.2"/><circle cx="7.6" cy="7.6" r="2.1"/>'
        '<circle cx="16.4" cy="16.4" r="2.1"/>',
        "percent",
    ),
    "insights": (
        '<path d="M12 3.4v2.2M12 18.4v2.2M3.4 12h2.2M18.4 12h2.2"/>'
        '<path d="m6 6 1.6 1.6M16.4 16.4 18 18M18 6l-1.6 1.6M7.6 16.4 6 18"/>'
        '<circle cx="12" cy="12" r="3.4"/>',
        "auto_awesome",
    ),
    "bulb": (
        '<path d="M9.4 17.6h5.2M10.2 20.6h3.6"/>'
        '<path d="M12 3.4a5.6 5.6 0 0 0-3.4 10.1c.6.4.9 1 .9 1.7h5c0-.7.3-1.3.9-1.7A5.6 '
        '5.6 0 0 0 12 3.4z"/>',
        "lightbulb",
    ),
    # --- dinheiro -----------------------------------------------------------
    "money": (
        '<rect x="2.6" y="6" width="18.8" height="12" rx="2.2"/>'
        '<circle cx="12" cy="12" r="2.7"/><path d="M6.2 9.6h.02M17.8 14.4h.02"/>',
        "payments",
    ),
    "cash_in": (
        '<path d="M3.4 20.4h17.2"/><path d="M12 16.6V4.4"/>'
        '<path d="m7.6 9 4.4-4.6L16.4 9"/>',
        "arrow_upward",
    ),
    "cash_out": (
        '<path d="M3.4 20.4h17.2"/><path d="M12 4.4v12.2"/>'
        '<path d="m7.6 12 4.4 4.6 4.4-4.6"/>',
        "arrow_downward",
    ),
    "card": (
        '<rect x="2.6" y="5.6" width="18.8" height="12.8" rx="2.2"/>'
        '<path d="M2.6 10h18.8"/><path d="M6.2 14.6h3.6"/>',
        "credit_card",
    ),
    "receipt": (
        '<path d="M6 3.4h12v17.2l-3-1.8-3 1.8-3-1.8-3 1.8z"/>'
        '<path d="M9 8.6h6M9 12.6h6"/>',
        "receipt_long",
    ),
    "bank": (
        '<path d="M3.4 9.6 12 4.4l8.6 5.2"/><path d="M4.8 9.6v8.8M19.2 9.6v8.8"/>'
        '<path d="M9 9.6v8.8M15 9.6v8.8"/><path d="M3.4 20.6h17.2"/>',
        "account_balance",
    ),
    # --- ações --------------------------------------------------------------
    "plus": ('<path d="M12 4.8v14.4M4.8 12h14.4"/>', "add"),
    "minus": ('<path d="M4.8 12h14.4"/>', "remove"),
    "trash": (
        '<path d="M4.4 6.4h15.2"/><path d="M9.4 6.4V4.6h5.2v1.8"/>'
        '<path d="M6.4 6.4 7.5 20.4h9L17.6 6.4"/><path d="M10.4 10v6.4M13.6 10v6.4"/>',
        "delete",
    ),
    "save": (
        '<path d="M4.6 6.6a2 2 0 0 1 2-2h8.2l4.6 4.6v8.2a2 2 0 0 1-2 2h-10.8a2 2 0 0 '
        '1-2-2z"/><path d="M8.6 4.6v4.8h5.6V4.6"/>'
        '<rect x="8.2" y="13.2" width="7.6" height="6.2" rx="1"/>',
        "save",
    ),
    "edit": (
        '<path d="m14.4 4.6 5 5"/><path d="M4.6 19.4h4.8L19.4 9.6l-5-5L4.6 14.6z"/>',
        "edit",
    ),
    "search": ('<circle cx="10.6" cy="10.6" r="6"/><path d="m15 15 5.4 5.4"/>', "search"),
    "filter": (
        '<path d="M3.4 5.4h17.2l-6.6 7.7v6.9l-4-2.2v-4.7z"/>',
        "filter_alt",
    ),
    "download": (
        '<path d="M12 3.6v11.2"/><path d="m7.6 10.4 4.4 4.4 4.4-4.4"/>'
        '<path d="M4.4 19.6h15.2"/>',
        "download",
    ),
    "refresh": (
        '<path d="M20.2 12a8.2 8.2 0 1 1-2.7-6.1"/><path d="M20.4 4.2v4.4h-4.4"/>',
        "refresh",
    ),
    "list": (
        '<path d="M8.6 6.6h11.8M8.6 12h11.8M8.6 17.4h11.8"/>'
        '<path d="M4.2 6.6h.02M4.2 12h.02M4.2 17.4h.02"/>',
        "list",
    ),
    "settings": (
        '<path d="M4.2 7.4h9.2M18.2 7.4h1.6M4.2 16.6h1.6M10.2 16.6h9.6"/>'
        '<circle cx="16" cy="7.4" r="2.2"/><circle cx="8" cy="16.6" r="2.2"/>',
        "tune",
    ),
    "calendar": (
        '<rect x="3.6" y="5.4" width="16.8" height="15" rx="2.2"/>'
        '<path d="M3.6 10h16.8"/><path d="M8.2 3.4v4M15.8 3.4v4"/>',
        "calendar_month",
    ),
    "clock": ('<circle cx="12" cy="12" r="8.4"/><path d="M12 7v5.3l3.3 2"/>', "schedule"),
    "tag": (
        '<path d="M11.2 3.6h9.2v9.2l-8.6 8.6a1.6 1.6 0 0 1-2.2 0l-7-7a1.6 1.6 0 0 1 '
        '0-2.2z"/><circle cx="16.4" cy="7.6" r="1.5"/>',
        "sell",
    ),
    "mail": (
        '<rect x="2.8" y="5.4" width="18.4" height="13.2" rx="2.2"/>'
        '<path d="m3.4 7 8.6 6 8.6-6"/>',
        "mail",
    ),
    "phone": (
        '<path d="M7.4 3.6h3.2l1.6 4-2.1 1.5a11 11 0 0 0 4.8 4.8l1.5-2.1 4 1.6v3.2a2 2 '
        '0 0 1-2.2 2A16.6 16.6 0 0 1 5.4 5.8a2 2 0 0 1 2-2.2z"/>',
        "call",
    ),
    "trophy": (
        '<path d="M8.4 4.4h7.2v5.3a3.6 3.6 0 0 1-7.2 0z"/>'
        '<path d="M8.4 6H5.8v1.5a3.1 3.1 0 0 0 2.7 3"/>'
        '<path d="M15.6 6h2.6v1.5a3.1 3.1 0 0 1-2.7 3"/>'
        '<path d="M12 13.3v3.5"/><path d="M8.6 19.9h6.8"/>',
        "trophy",
    ),
    # --- estado -------------------------------------------------------------
    "check": ('<path d="m4.8 12.6 4.6 4.6 9.8-11"/>', "check"),
    "check_circle": (
        '<circle cx="12" cy="12" r="8.4"/><path d="m8.4 12.2 2.6 2.6 4.6-5.2"/>',
        "check_circle",
    ),
    "x": ('<path d="m6 6 12 12M18 6 6 18"/>', "close"),
    "x_circle": (
        '<circle cx="12" cy="12" r="8.4"/><path d="m9.2 9.2 5.6 5.6M14.8 9.2l-5.6 5.6"/>',
        "cancel",
    ),
    "alert": (
        '<path d="M12 4.4 3 20h18z"/><path d="M12 10v4.2"/><path d="M12 17.2h.02"/>',
        "warning",
    ),
    "info": (
        '<circle cx="12" cy="12" r="8.4"/><path d="M12 11.2v5.4"/>'
        '<path d="M12 7.8h.02"/>',
        "info",
    ),
    "empty": (
        '<path d="M3.6 13.4 6.2 5.2h11.6l2.6 8.2"/>'
        '<path d="M3.6 13.4h4.8l1.2 2.6h4.8l1.2-2.6h4.8v5.4H3.6z"/>',
        "inbox",
    ),
}

ICONS: dict[str, Icon] = {
    name: Icon(name=name, body=body, material=f":material/{mat}:")
    for name, (body, mat) in _PATHS.items()
}


def icon(name: str, size: int = 20, stroke: float = 1.7) -> str:
    """SVG inline do ícone. Nome desconhecido cai em um placeholder neutro."""
    ico = ICONS.get(name)
    if ico is None:
        return _SVG_TPL.format(size=size, sw=stroke, body='<circle cx="12" cy="12" r="8"/>')
    return ico.svg(size=size, stroke=stroke)


def material(name: str) -> str:
    """Nome Material equivalente, para os parâmetros `icon=` do Streamlit."""
    ico = ICONS.get(name)
    return ico.material if ico else ":material/circle:"


def label(name: str, text: str) -> str:
    """Ícone + texto para labels de widgets nativos (Streamlit renderiza Material)."""
    return f"{material(name)} {escape(text, quote=False)}"


__all__ = ["Icon", "ICONS", "icon", "material", "label"]
