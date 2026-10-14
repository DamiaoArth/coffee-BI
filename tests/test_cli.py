import os
from pathlib import Path

import pytest

from coffee_bi import cli


@pytest.fixture
def clean_config(monkeypatch):
    # No local .env should influence these tests.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    for key in [
        "COFFEE_BI_MODE",
        "DATABASE_URL",
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD",
        "CAIXA_PASSWORD",
        "COOKIE_SECURE",
    ]:
        monkeypatch.setenv(key, os.environ.get(key, ""))
        monkeypatch.delenv(key)


def test_dev_overrides_remote_database_and_https_cookie(
    clean_config, monkeypatch, tmp_path
):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unavailable.example/coffee")
    monkeypatch.setenv("ADMIN_PASSWORD", "production-password")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    parser = cli.parser()
    folder = tmp_path / "pasta com espaço e café"
    args = parser.parse_args(["init", "--dev", "--data-dir", str(folder)])
    target = cli.configure(args, parser)
    assert target == folder / "dev.sqlite3"
    assert folder.is_dir()
    assert os.environ["DATABASE_URL"] == "sqlite:///" + target.as_posix()
    assert os.environ["ADMIN_USERNAME"] == "dev"
    assert os.environ["ADMIN_PASSWORD"] == "dev12345"
    assert os.environ["COOKIE_SECURE"] == "false"
    assert os.environ["CAIXA_PASSWORD"] == ""


def test_default_local_path_is_independent_of_working_directory(
    clean_config, monkeypatch, tmp_path
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    command_parser = cli.parser()
    args = command_parser.parse_args(["init", "--dev"])
    first = cli.configure(args, command_parser)
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    assert (
        cli.configure(args, command_parser)
        == first
        == tmp_path / ".coffee-bi" / "dev.sqlite3"
    )


def test_standard_mode_preserves_environment(clean_config, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://db/coffee")
    monkeypatch.setenv("ADMIN_USERNAME", "owner")
    monkeypatch.setenv("ADMIN_PASSWORD", "owner-password")
    command_parser = cli.parser()
    assert cli.configure(command_parser.parse_args(["init"]), command_parser) is None
    assert os.environ["DATABASE_URL"] == "postgresql://db/coffee"
    assert os.environ["ADMIN_USERNAME"] == "owner"
    assert os.environ["ADMIN_PASSWORD"] == "owner-password"
    assert os.environ["COFFEE_BI_MODE"] == "standard"


@pytest.mark.parametrize(
    "arguments",
    [
        ["init", "--dev", "--host", "0.0.0.0"],
        ["init", "--data-dir", "local"],
        ["init", "--port", "0"],
        ["init", "--port", "65536"],
        ["init", "--port", "no"],
    ],
)
def test_invalid_options_do_not_start_server(clean_config, monkeypatch, arguments):
    monkeypatch.setattr(
        "uvicorn.run", lambda *args, **kwargs: pytest.fail("Server started")
    )
    with pytest.raises(SystemExit) as error:
        cli.main(arguments)
    assert error.value.code == 2


def test_launcher_uses_import_string_for_spawned_reload_worker(
    clean_config, monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setattr(
        "uvicorn.run", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    cli.main(["init", "--dev", "--data-dir", str(tmp_path), "--port", "8123"])
    args, kwargs = calls[0]
    assert args == ("api.main:app",)
    assert kwargs["reload"] is True
    assert kwargs["port"] == 8123
    assert kwargs["host"] == "127.0.0.1"
