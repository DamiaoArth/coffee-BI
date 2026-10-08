"""Comando BI init: inicia a aplicação FastAPI + frontend + Firestore.

Instalação única: python -m pip install -e .
Depois: BI init
"""
from __future__ import annotations

import argparse
import getpass
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_PLACEHOLDERS = {"", "seu-firebase-project-id", "your-firebase-project-id"}


def _say(message: str) -> None:
    print(message, flush=True)


def _write_private_file(path: Path, content: str) -> None:
    # Service-account files are never created here; only the local .env.
    path.write_text(content, encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def _replace_env(path: Path, key: str, value: str) -> None:
    original = path.read_text(encoding="utf-8")
    matcher = re.compile(r"^" + re.escape(key) + r"=.*$", re.MULTILINE)
    if matcher.search(original):
        updated = matcher.sub(lambda match: f"{key}={value}", original)
    else:
        updated = original.rstrip("\n") + f"\n{key}={value}\n"
    _write_private_file(path, updated)
    os.environ[key] = value


def ensure_config(*, emulator: bool) -> bool:
    """Create .env on first invocation and check the *actual* destination."""
    path = PROJECT_ROOT / ".env"
    if not path.exists():
        sample = PROJECT_ROOT / ".env.example"
        if not sample.is_file():
            _say("Erro: .env.example não foi encontrado no repositório.")
            return False
        _write_private_file(path, sample.read_text(encoding="utf-8"))
        _say("[BI] Configuração local criada: .env (não é enviada ao GitHub).")
    load_dotenv(path, override=False)

    production = os.getenv("APP_ENV", "development").lower() == "production"
    if production and (emulator or os.getenv("FIRESTORE_EMULATOR_HOST")):
        _say("Erro: o emulador Firestore não pode ser usado com APP_ENV=production.")
        return False

    secret = os.getenv("SESSION_SECRET", "").strip()
    if production:
        if len(secret) < 32:
            _say("Erro: configure um SESSION_SECRET fixo com pelo menos 32 caracteres no ambiente de produção.")
            return False
    elif not secret:
        secret = secrets.token_urlsafe(48)
        _replace_env(path, "SESSION_SECRET", secret)
        _say("[BI] SESSION_SECRET forte gerado e salvo localmente.")

    if emulator:
        # Explicit emulator mode MUST NOT accidentally point at production.
        os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
        os.environ["FIREBASE_PROJECT_ID"] = "demo-coffee-bi"
        return True

    project = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    if project in PROJECT_PLACEHOLDERS:
        if sys.stdin.isatty():
            project = input("ID do projeto Firebase (ex.: business-inteli): ").strip()
            if project and project not in PROJECT_PLACEHOLDERS:
                _replace_env(path, "FIREBASE_PROJECT_ID", project)
        if project in PROJECT_PLACEHOLDERS:
            _say("Erro: configure FIREBASE_PROJECT_ID no .env (ID exato do seu Firebase).")
            _say("Ou rode BI init --emulator para testar sem projeto Firebase.")
            return False
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        key_file = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).expanduser()
        if not key_file.is_file():
            _say("Erro: GOOGLE_APPLICATION_CREDENTIALS aponta para um arquivo inexistente.")
            return False
    return True


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.8):
            return True
    except OSError:
        return False


def _emulator_command() -> list[str]:
    firebase = shutil.which("firebase")
    if firebase:
        return [firebase, "emulators:start", "--only", "firestore",
                "--project", "demo-coffee-bi"]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "firebase-tools@latest", "emulators:start",
                "--only", "firestore", "--project", "demo-coffee-bi"]
    raise RuntimeError(
        "Firebase CLI não encontrada. Instale Node.js e execute "
        "'npm install -g firebase-tools', ou use o Firebase na nuvem."
    )


def start_emulator():
    """Start only when explicitly requested or configured in .env."""
    host = os.getenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    if host not in {"127.0.0.1:8080", "localhost:8080"}:
        _say(f"[BI] Conectando ao emulador externo existente em {host}.")
        return None
    if _port_open("127.0.0.1", 8080):
        _say("[BI] Firestore Emulator já está ativo na porta 8080.")
        return None

    cmd = _emulator_command()
    _say("[BI] Iniciando Firestore Emulator local...")
    process = subprocess.Popen(
        cmd, cwd=PROJECT_ROOT, env=os.environ.copy()
    )
    end = time.monotonic() + 70
    while time.monotonic() < end:
        if process.poll() is not None:
            raise RuntimeError(
                "Firestore Emulator encerrou antes de iniciar. "
                "Verifique Node.js, Java e Firebase CLI."
            )
        if _port_open("127.0.0.1", 8080):
            return process
        time.sleep(0.4)
    raise RuntimeError("Não foi possível conectar ao Firestore Emulator na porta 8080.")


def stop_emulator(process) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=6)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def verify_firestore():
    """Do not start a dashboard disconnected from its configured database."""
    from api.firebase_db import get_firestore

    db = get_firestore()
    db.collection("_health").document("check").get(timeout=12)
    return db


def first_admin_setup(db) -> bool:
    """Interactive one-time account bootstrap; no default or hardcoded passwords."""
    if next(iter(db.collection("users").limit(1).stream()), None) is not None:
        return True
    _say("[BI] Banco vazio: crie a primeira conta de administrador.")
    if not sys.stdin.isatty():
        _say(
            "Erro: execute BI init em um terminal interativo para criar o administrador; "
            "alternativamente rode 'python -m api.bootstrap_admin'."
        )
        return False
    username = input("Usuário administrador [admin]: ").strip() or "admin"
    password = getpass.getpass("Senha do administrador (mínimo 10 caracteres): ")
    if len(password) < 10:
        _say("Erro: a senha deve ter no mínimo 10 caracteres.")
        return False
    confirmation = getpass.getpass("Repita a senha: ")
    if password != confirmation:
        _say("Erro: as senhas não coincidem.")
        return False
    from api.main import register_user
    from api.passwords import PasswordService

    register_user(
        db, username=username,
        password_hash=PasswordService.hash_password(password),
        role="admin",
    )
    _say("[BI] Administrador registrado no Firestore.")
    return True


def _open_browser(host: str, port: int) -> None:
    if host == "0.0.0.0":
        host = "127.0.0.1"
    elif host == "::":
        host = "::1"
    url = f"http://{host}:{port}/"
    # Browser opening is strictly best effort, not required for the app.
    for _ in range(70):
        if _port_open(host, port):
            webbrowser.open(url)
            return
        time.sleep(0.25)


def init(args: argparse.Namespace) -> int:
    os.chdir(PROJECT_ROOT)
    emulator_proc = None
    try:
        if not ensure_config(emulator=args.emulator):
            return 2
        use_emulator = bool(os.getenv("FIRESTORE_EMULATOR_HOST"))
        if use_emulator:
            emulator_proc = start_emulator()
        _say("[BI] Verificando conexão com " + (
            "Firestore Emulator..." if use_emulator else "Cloud Firestore..."
        ))
        db = verify_firestore()
        if not first_admin_setup(db):
            return 2

        import uvicorn
        _say(f"[BI] Frontend + FastAPI disponíveis em http://127.0.0.1:{args.port}")
        _say("[BI] Para encerrar, pressione Ctrl+C.")
        if not args.no_browser:
            threading.Thread(
                target=_open_browser, args=(args.host, args.port), daemon=True
            ).start()
        uvicorn.run(
            "api.main:app", host=args.host, port=args.port,
            reload=args.reload, reload_dirs=[str(PROJECT_ROOT)] if args.reload else None,
        )
        return 0
    except KeyboardInterrupt:
        _say("\n[BI] Encerrando.")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        _say(f"[BI] Não foi possível iniciar: {exc}")
        _say("[BI] Confira seu .env, acesso ao Firebase e permissões ADC.")
        return 1
    finally:
        stop_emulator(emulator_proc)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="BI", description="Coffee BI — inicialização do ERP"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("init", help="Iniciar frontend, API e Firestore configurado")
    start.add_argument("--host", default="127.0.0.1", help="Interface de escuta da API")
    start.add_argument("--port", type=int, default=8000, help="Porta HTTP (padrão 8000)")
    start.add_argument("--emulator", action="store_true",
                       help="Iniciar Firebase Emulator local (sem credenciais reais)")
    start.add_argument("--reload", action="store_true",
                       help="Reiniciar automaticamente ao alterar código")
    start.add_argument("--no-browser", action="store_true",
                       help="Não abrir a aplicação no navegador")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.port < 1 or args.port > 65535:
        _say("Erro: escolha uma porta entre 1 e 65535.")
        return 2
    if args.command == "init":
        return init(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
