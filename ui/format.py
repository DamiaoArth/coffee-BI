"""Formatação pt-BR para valores exibidos na interface."""

from __future__ import annotations

from datetime import date, time


def brl(value) -> str:
    """Formata em Real com separador de milhar e vírgula decimal."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "R$ 0,00"
    inteiro, _, decimal = f"{n:,.2f}".partition(".")
    return f"R$ {inteiro.replace(',', '.')},{decimal}"


def num(value, casas: int = 0) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "0"
    inteiro, _, decimal = f"{n:,.{casas}f}".partition(".")
    inteiro = inteiro.replace(",", ".")
    return f"{inteiro},{decimal}" if decimal else inteiro


def pct(value, casas: int = 1) -> str:
    try:
        return f"{float(value):.{casas}f}".replace(".", ",") + "%"
    except (TypeError, ValueError):
        return "0,0%"


def signed_pct(value, casas: int = 1) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "0,0%"
    return f"{'+' if n >= 0 else '-'}{abs(n):.{casas}f}".replace(".", ",") + "%"


def data_br(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else "—"


def hora_br(value: time | None) -> str:
    return value.strftime("%H:%M") if value else "—"


def plural(n: int, singular: str, plural_: str) -> str:
    return f"{n} {singular if n == 1 else plural_}"


__all__ = ["brl", "num", "pct", "signed_pct", "data_br", "hora_br", "plural"]
