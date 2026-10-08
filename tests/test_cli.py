"""Behavioral tests for BI init without touching real Firebase."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import pytest

from api import cli


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    for name in (
        "FIREBASE_PROJECT_ID", "FIRESTORE_EMULATOR_HOST",
        "SESSION_SECRET", "APP_ENV", "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env.example").write_text(
        "APP_ENV=development\n"
        "FIREBASE_PROJECT_ID=seu-firebase-project-id\n"
        "SESSION_SECRET=\n",
        encoding="utf-8",
    )
    return tmp_path


def test_init_creates_secret_and_isolated_emulator_env(isolated, monkeypatch, capsys):
    assert cli.ensure_config(emulator=True) is True
    conf = (isolated / ".env").read_text(encoding="utf-8")
    match = re.search(r"^SESSION_SECRET=(\S+)$", conf, re.MULTILINE)
    assert match is not None and len(match.group(1)) >= 60
    assert os.environ["SESSION_SECRET"] == match.group(1)
    assert os.environ["FIREBASE_PROJECT_ID"] == "demo-coffee-bi"
    assert os.environ["FIRESTORE_EMULATOR_HOST"] == "127.0.0.1:8080"
    assert match.group(1) not in capsys.readouterr().out
    if os.name != "nt":
        assert (isolated / ".env").stat().st_mode & 0o077 == 0


def test_cloud_requires_project_id_without_prompt(isolated, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", open(os.devnull, "r"))
    try:
        assert cli.ensure_config(emulator=False) is False
        assert "FIREBASE_PROJECT_ID" in capsys.readouterr().out
    finally:
        sys.stdin.close()


def test_cloud_uses_existing_configuration(isolated, monkeypatch):
    (isolated / ".env").write_text(
        "APP_ENV=development\nFIREBASE_PROJECT_ID=business-inteli\n"
        "SESSION_SECRET=exemplo_segredo_para_teste_local_nao_usar_em_producao\n",
        encoding="utf-8",
    )
    assert cli.ensure_config(emulator=False) is True
    assert os.environ["FIREBASE_PROJECT_ID"] == "business-inteli"


def test_production_rejects_emulator(isolated, monkeypatch, capsys):
    (isolated / ".env").write_text(
        "APP_ENV=production\nSESSION_SECRET=" + "A" * 48 + "\n",
        encoding="utf-8",
    )
    assert cli.ensure_config(emulator=True) is False
    assert "production" in capsys.readouterr().out


def test_init_starts_backend_with_emulator_and_cleans_up(isolated, monkeypatch):
    from api import cli as module

    monkeypatch.setattr(module, "ensure_config", lambda *, emulator: (
        os.environ.update({
            "FIRESTORE_EMULATOR_HOST": "127.0.0.1:8080",
            "FIREBASE_PROJECT_ID": "demo-coffee-bi",
        }) or True
    ))
    process = object()
    lifecycle = []
    monkeypatch.setattr(module, "start_emulator", lambda: lifecycle.append("start") or process)
    monkeypatch.setattr(module, "verify_firestore", lambda: lifecycle.append("firestore") or object())
    monkeypatch.setattr(module, "first_admin_setup", lambda db: lifecycle.append("admin") or True)
    monkeypatch.setattr(module, "stop_emulator", lambda proc: lifecycle.append(("stop", proc)))

    import uvicorn
    monkeypatch.setattr(
        uvicorn, "run", lambda app, **kwargs: lifecycle.append(
            ("api", app, kwargs["port"], kwargs["host"])
        ),
    )
    args = argparse.Namespace(
        emulator=True, port=8123, host="127.0.0.1",
        reload=False, no_browser=True,
    )
    assert module.init(args) == 0
    assert lifecycle == [
        "start", "firestore", "admin",
        ("api", "api.main:app", 8123, "127.0.0.1"), ("stop", process),
    ]


def test_invalid_port():
    assert cli.main(["init", "--port", "0"]) == 2
    assert cli.main(["init", "--port", "65536"]) == 2


def test_seed_command_uses_configured_project(monkeypatch, tmp_path):
    from api import seed_firestore

    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "ensure_config", lambda *, emulator: True)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "business-inteli")
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    called = {}

    def fake_seed(argv):
        called["argv"] = argv
        return 0

    monkeypatch.setattr(seed_firestore, "main", fake_seed)
    assert cli.main(["seed", "--yes", "--days", "14"]) == 0
    assert called["argv"] == [
        "--days", "14", "--apply", "--confirm-project-id", "business-inteli"
    ]
