import bcrypt
from sqlalchemy.orm import Session
from models.database_models import Usuario
from datetime import datetime

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def authenticate(db: Session, username: str, password: str) -> Usuario:
        user = db.query(Usuario).filter(
            Usuario.nome_usuario == username,
            Usuario.ativo == True
        ).first()
        
        if user and AuthService.verify_password(password, user.senha_hash):
            user.ultimo_acesso = datetime.now()
            db.commit()
            return user
        return None
    
    @staticmethod
    def criar_usuario(db: Session, nome_usuario: str, senha: str, 
                     nivel_acesso: str, funcionario_id: int = None) -> Usuario:
        senha_hash = AuthService.hash_password(senha)
        novo_usuario = Usuario(
            nome_usuario=nome_usuario,
            senha_hash=senha_hash,
            nivel_acesso=nivel_acesso,
            funcionario_id=funcionario_id
        )
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return novo_usuario