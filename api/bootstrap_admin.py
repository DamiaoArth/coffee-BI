"""Provisionamento explícito: nenhuma senha de administrador padrão."""
import argparse
from getpass import getpass
from config.database import SessionLocal, init_db
from models.database_models import Usuario
from services.auth_service import AuthService

def main():
    parser = argparse.ArgumentParser(description="Configurar a conta de administrador")
    parser.add_argument("--username", default="admin")
    args = parser.parse_args()
    password = getpass("Senha do administrador (mínimo 10 caracteres): ")
    if len(password) < 10:
        raise SystemExit("Escolha uma senha de ao menos 10 caracteres.")
    init_db()
    with SessionLocal() as db:
        user = db.query(Usuario).filter(Usuario.nome_usuario == args.username).first()
        if user:
            user.senha_hash = AuthService.hash_password(password)
            user.nivel_acesso = "admin"
            user.ativo = True
        else:
            db.add(Usuario(nome_usuario=args.username, senha_hash=AuthService.hash_password(password),
                           nivel_acesso="admin", ativo=True))
        db.commit()
    print("Administrador configurado com sucesso.")

if __name__ == "__main__":
    main()
