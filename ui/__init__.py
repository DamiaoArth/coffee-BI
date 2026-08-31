"""Design system do ERP Cafeteria."""

from ui.theme import apply_theme
from ui.page import setup_page, role_label, ROLES_GESTAO
from ui.icons import icon, material, ICONS
from ui.components import (
    page_header, section, kpi_card, kpi_row, notice, badge, empty_state,
    definition_list, line_item, total_line, sidebar_identity, sidebar_nav,
    data_table, download_csv,
)
from ui.format import brl, num, pct, signed_pct, data_br, hora_br, plural

__all__ = [
    "apply_theme", "setup_page", "role_label", "ROLES_GESTAO",
    "icon", "material", "ICONS",
    "page_header", "section", "kpi_card", "kpi_row", "notice", "badge",
    "empty_state", "definition_list", "line_item", "total_line",
    "sidebar_identity", "sidebar_nav", "data_table", "download_csv",
    "brl", "num", "pct", "signed_pct", "data_br", "hora_br", "plural",
]
