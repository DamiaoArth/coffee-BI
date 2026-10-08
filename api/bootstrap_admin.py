"""Create or explicitly reset the first admin account in Firestore.

Usage:
    python -m api.bootstrap_admin --username admin
Secrets are read from the terminal, never from command-line arguments.
"""
import argparse
from getpass import getpass

from api.firebase_db import get_firestore, ref, user_lookup_ref
from api.main import register_user
from api.passwords import PasswordService


def main():
    parser = argparse.ArgumentParser(description="Configurar administrador no Firebase")
    parser.add_argument("--username", default="admin")
    args = parser.parse_args()
    password = getpass("Senha forte do administrador (mínimo 10 caracteres): ")
    if len(password) < 10:
        raise SystemExit("Escolha uma senha de no mínimo 10 caracteres.")

    db = get_firestore()
    index = user_lookup_ref(db, args.username).get()
    if index.exists:
        uid = index.to_dict()["user_id"]
        doc = ref(db, "users", uid)
        if not doc.get().exists:
            raise SystemExit("Índice de usuário inconsistente. Corrija antes de prosseguir.")
        doc.update({
            "senha_hash": PasswordService.hash_password(password),
            "nivel_acesso": "admin",
            "ativo": True,
        })
        print("Senha e permissões do administrador atualizadas no Firestore.")
    else:
        register_user(
            db, username=args.username,
            password_hash=PasswordService.hash_password(password),
            role="admin",
        )
        print("Administrador criado no Firestore com sucesso.")


if __name__ == "__main__":
    main()
