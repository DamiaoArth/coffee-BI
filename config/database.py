import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./cafeteria.db",  # SQLite para desenvolvimento
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"check_same_thread": False, "timeout": 30}
    if DATABASE_URL.startswith("sqlite")
    else {},
)

if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_constraints(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    from models.database_models import Base

    Base.metadata.create_all(bind=engine)
    # Additive migration: existing SQLite/PostgreSQL databases keep their data.
    if "custo_unitario" not in {
        c["name"] for c in inspect(engine).get_columns("itens_venda")
    }:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE itens_venda ADD COLUMN custo_unitario NUMERIC(10, 2)")
            )
    if "version" not in {c["name"] for c in inspect(engine).get_columns("produtos")}:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE produtos ADD COLUMN version INTEGER NOT NULL DEFAULT 1"
                )
            )
