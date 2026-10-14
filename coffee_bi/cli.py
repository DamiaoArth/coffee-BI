"""Console entry point. Configure the process before importing the application."""

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def port_number(value):
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("A porta deve ser um número.") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("A porta deve estar entre 1 e 65535.")
    return port


def parser():
    result = argparse.ArgumentParser(
        prog="BI", description="Inicia o Coffee BI e sua API."
    )
    commands = result.add_subparsers(dest="command", required=True)
    start = commands.add_parser(
        "init", help="Prepara o banco e inicia a interface e a API."
    )
    start.add_argument(
        "--dev",
        action="store_true",
        help="SQLite local, acesso dev e recarga automática.",
    )
    start.add_argument(
        "--host", default="127.0.0.1", help="Endereço do servidor (padrão: 127.0.0.1)."
    )
    start.add_argument(
        "--port", type=port_number, default=8000, help="Porta HTTP (padrão: 8000)."
    )
    start.add_argument(
        "--data-dir", type=Path, help="Pasta do banco local; somente com --dev."
    )
    return result


def configure(args, command_parser):
    # The same .env is loaded even when BI is invoked outside the checkout.
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    os.environ["COFFEE_BI_MODE"] = "dev" if args.dev else "standard"
    if not args.dev:
        if args.data_dir is not None:
            command_parser.error("--data-dir exige --dev.")
        return None
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        command_parser.error(
            "--dev usa acesso local. Utilize --host 127.0.0.1 ou localhost."
        )
    data_dir = (args.data_dir or Path.home() / ".coffee-bi").expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    database = data_dir / "dev.sqlite3"
    # Explicit overrides must precede config.database import, including in the
    # Windows spawned reload worker. The production .env is never rewritten.
    os.environ.update(
        DATABASE_URL="sqlite:///" + database.as_posix(),
        ADMIN_USERNAME="dev",
        ADMIN_PASSWORD="dev12345",
        CAIXA_PASSWORD="",
        COOKIE_SECURE="false",
    )
    return database


def main(argv=None):
    command_parser = parser()
    args = command_parser.parse_args(argv)
    try:
        database = configure(args, command_parser)
    except OSError as exc:
        command_parser.exit(1, f"Não foi possível preparar a pasta local: {exc}\n")

    host = f"[{args.host}]" if ":" in args.host else args.host
    url = f"http://{host}:{args.port}"
    print(f"Coffee BI: {url}\nAPI: {url}/docs", flush=True)
    if database:
        print(
            f"Modo de desenvolvimento | Banco: {database}\n"
            "Acesso local: dev / dev12345\n"
            "Os dados são preservados ao reiniciar. Ctrl+C encerra o servidor.",
            flush=True,
        )
    else:
        print(
            "Configuração padrão: banco e usuários definidos no ambiente/.env.",
            flush=True,
        )
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.dev,
        reload_dirs=[str(ROOT)] if args.dev else None,
    )
