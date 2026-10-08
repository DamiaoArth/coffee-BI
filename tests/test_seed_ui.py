"""Pure tests for the demo Firestore seed and frontend design contract."""
from datetime import date

from api.seed_firestore import SEED_TAG, build_dataset


def test_seed_dataset_is_coherent_and_reasonably_sized():
    dataset = build_dataset(date(2026, 10, 8), 30)
    assert len(dataset["products"]) == 10
    assert len(dataset["employees"]) == 3
    assert 60 <= len(dataset["sales"]) <= 180
    assert len(dataset["purchases"]) == 3
    assert len(dataset["transactions"]) == 5

    product_names = {p["nome"] for p in dataset["products"]}
    for sale in dataset["sales"]:
        assert sale["valor_total_centavos"] == sum(
            line["subtotal_centavos"] for line in sale["itens"]
        )
        assert all(line["nome"] in product_names for line in sale["itens"])
        assert all(
            line["subtotal_centavos"]
            == line["preco_unitario_centavos"] * line["quantidade"]
            for line in sale["itens"]
        )

    for purchase in dataset["purchases"]:
        assert purchase["valor_total_centavos"] == sum(
            line["subtotal_centavos"] for line in purchase["itens"]
        )
        assert all(line["nome"] in product_names for line in purchase["itens"])


def test_seed_range_is_bounded():
    low = build_dataset(date(2026, 10, 8), 1)
    high = build_dataset(date(2026, 10, 8), 500)
    assert len({sale["data"] for sale in low["sales"]}) <= 7
    assert len({sale["data"] for sale in high["sales"]}) <= 90
    assert SEED_TAG == "coffee-bi-demo-v1"


def test_frontend_no_longer_uses_character_glyphs_as_icons():
    source = open("web/app.js", encoding="utf-8").read()
    for bad in ("▦", "◫", "▤", "▧", "◈", "◉", "♙", "☕", "↗", "↙", "◎"):
        assert bad not in source
    assert "const ICONS =" in source
    assert "class=\"btn btn-primary\"" in source
    assert "class=\"nav-track\"" in source


def test_dashboard_charts_are_interactive_and_accessible():
    source = open("web/app.js", encoding="utf-8").read()
    css = open("web/styles.css", encoding="utf-8").read()
    for token in (
        "chart-metric", "chart-compare", "chart-point",
        "payment-select", "rank-select", "viz-tooltip",
        "serie_anterior", "aria-pressed"
    ):
        assert token in source
    for token in (
        ".chart-segmented", ".chart-line-compare", ".donut-layout",
        ".rank-bar-row", ".viz-tooltip", ".period-switch"
    ):
        assert token in css
