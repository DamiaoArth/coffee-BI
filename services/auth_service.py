from datetime import datetime

import bcrypt
from sqlalchemy.orm import Session

from models.database_models import LoginSession, Usuario


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        if (
            not isinstance(password, str)
            or len(password) < 6
            or len(password.encode("utf-8")) > 72
        ):
            raise ValueError(
                "Senha deve ter no mínimo 6 caracteres e no máximo 72 bytes UTF-8."
            )
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    @staticmethod
    def authenticate(db: Session, username: str, password: str) -> Usuario:
        user = (
            db.query(Usuario)
            .filter(Usuario.nome_usuario == username, Usuario.ativo.is_(True))
            .first()
        )

        if (
            user
            and (not user.funcionario or user.funcionario.ativo)
            and AuthService.verify_password(password, user.senha_hash)
        ):
            user.ultimo_acesso = datetime.now()
            db.commit()
            return user
        return None

    @staticmethod
    def criar_usuario(
        db: Session,
        nome_usuario: str,
        senha: str,
        nivel_acesso: str,
        funcionario_id: int = None,
        commit: bool = True,
    ) -> Usuario:
        if (
            nivel_acesso not in {"admin", "caixa"}
            or not nome_usuario
            or not nome_usuario.strip()
        ):
            raise ValueError("Usuário ou nível de acesso inválido.")
        senha_hash = AuthService.hash_password(senha)
        novo_usuario = Usuario(
            nome_usuario=nome_usuario.strip(),
            senha_hash=senha_hash,
            nivel_acesso=nivel_acesso,
            funcionario_id=funcionario_id,
        )
        try:
            db.add(novo_usuario)
            if commit:
                db.commit()
                db.refresh(novo_usuario)
            else:
                db.flush()
            return novo_usuario
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def redefinir_senha(db, user_id, password):
        try:
            user = db.get(Usuario, user_id)
            if not user:
                raise ValueError("Usuário não encontrado.")
            user.senha_hash = AuthService.hash_password(password)
            db.query(LoginSession).filter_by(user_id=user_id).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
