"""Coffee BI HTTP application. Run: uvicorn api.main:app --reload."""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from api.schemas import Employee, Login, Movement, Product, Purchase, Transaction
from config.bootstrap import bootstrap_users
from config.clock import business_today
from config.database import get_db, init_db
from models.database_models import (
    Compra,
    Funcionario,
    LoginSession,
    Produto,
    Transacao,
    Usuario,
    Venda,
)
from services.auth_service import AuthService
from services.compra_service import CompraService
from services.venda_service import VendaService

log = logging.getLogger(__name__)
WEB = Path(__file__).resolve().parent.parent / "web"


@asynccontextmanager
async def lifespan(app):
    init_db()
    bootstrap_users()
    yield


app = FastAPI(title="Coffee BI API", version="2.0.0", lifespan=lifespan)


@app.middleware("http")
async def origin_guard(request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ValueError)
async def validation_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        {"detail": "Dados conflitantes ou referência inválida."}, status_code=409
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    log.error("Database operation failed", exc_info=exc)
    return JSONResponse(
        {"detail": "Não foi possível concluir a operação."}, status_code=500
    )


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("coffee_session", "")
    session = (
        db.get(LoginSession, sha256(token.encode()).hexdigest()) if token else None
    )
    if not session or session.expires_at <= datetime.now(timezone.utc).replace(
        tzinfo=None
    ):
        raise HTTPException(401, "Faça login para continuar.")
    user = db.get(Usuario, session.user_id)
    if not user or not user.ativo or (user.funcionario and not user.funcionario.ativo):
        raise HTTPException(401, "Acesso desativado.")
    return user


def admin(user: Usuario = Depends(current_user)):
    if user.nivel_acesso != "admin":
        raise HTTPException(403, "Esta operação exige acesso de administrador.")
    return user


def user_data(user):
    return {
        "id": user.id,
        "username": user.nome_usuario,
        "nivel_acesso": user.nivel_acesso,
    }


def serialize(row):
    data = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    if isinstance(row, (Venda, Compra)):
        data["itens"] = [
            {**serialize(i), "produto_nome": i.produto.nome} for i in row.itens
        ]
    return jsonable_encoder(data, custom_encoder={Decimal: str})


def persist(db, row):
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return serialize(row)
    except Exception:
        db.rollback()
        raise


def find(db, model, id):
    row = db.get(model, id)
    if not row:
        raise HTTPException(404, "Registro não encontrado.")
    return row


@app.post("/api/auth/login")
def login(
    payload: Login, request: Request, response: Response, db: Session = Depends(get_db)
):
    user = AuthService.authenticate(db, payload.username, payload.password)
    if not user or (user.funcionario and not user.funcionario.ativo):
        raise HTTPException(401, "Usuário ou senha inválidos.")
    old_token = request.cookies.get("coffee_session")
    if old_token:
        db.query(LoginSession).filter_by(
            token_hash=sha256(old_token.encode()).hexdigest()
        ).delete()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(LoginSession).filter(LoginSession.expires_at <= now).delete()
    token = secrets.token_urlsafe(32)
    db.add(
        LoginSession(
            token_hash=sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=now + timedelta(hours=8),
        )
    )
    db.commit()
    response.set_cookie(
        "coffee_session",
        token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE") == "true",
        samesite="strict",
        max_age=28800,
    )
    return user_data(user)


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return user_data(user)


@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("coffee_session", "")
    db.query(LoginSession).filter_by(
        token_hash=sha256(token.encode()).hexdigest()
    ).delete()
    db.commit()
    response.delete_cookie("coffee_session")


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


def listing(db, model, page, page_size, sort, direction, q, active=None):
    allowed = {c.name for c in model.__table__.columns} - {"senha_hash"}
    if sort not in allowed:
        raise HTTPException(422, "Coluna de ordenação inválida.")
    query = db.query(model)
    if q:
        field = getattr(model, "nome", getattr(model, "descricao", None))
        if model in (Venda, Compra):
            query = (
                query.filter(model.id == int(q))
                if q.isdecimal()
                else query.filter(model.id == -1)
            )
        elif field is not None:
            query = query.filter(
                field.ilike(
                    "%" + q.replace("%", "\\%").replace("_", "\\_") + "%", escape="\\"
                )
            )
    if active is not None and hasattr(model, "ativo"):
        query = query.filter(model.ativo == active)
    total = query.count()
    col = getattr(model, sort)
    query = query.order_by(
        col.desc() if direction == "desc" else col.asc(), model.id.asc()
    )
    return {
        "items": [
            serialize(r) for r in query.offset((page - 1) * page_size).limit(page_size)
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/products")
def products(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort: str = "nome",
    direction: str = Query("asc", pattern="^(asc|desc)$"),
    q: str = Query("", max_length=200),
    active: bool | None = None,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    return listing(db, Produto, page, page_size, sort, direction, q, active)


@app.get("/api/products/{id}")
def product(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    return serialize(find(db, Produto, id))


@app.post("/api/products", status_code=201)
def create_product(
    payload: Product, db: Session = Depends(get_db), user=Depends(admin)
):
    return persist(db, Produto(**payload.model_dump()))


@app.put("/api/products/{id}")
def update_product(
    id: int,
    payload: Product,
    if_match: int = Header(..., alias="If-Match", ge=1),
    db: Session = Depends(get_db),
    user=Depends(admin),
):
    find(db, Produto, id)
    result = db.execute(
        update(Produto)
        .where(Produto.id == id, Produto.version == if_match)
        .values(**payload.model_dump(), version=Produto.version + 1)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            409,
            "Produto ou estoque mudou. Reabra a edição para carregar os dados atuais.",
        )
    db.commit()
    db.expire_all()
    return serialize(find(db, Produto, id))


@app.delete("/api/products/{id}", status_code=204)
def delete_product(id: int, db: Session = Depends(get_db), user=Depends(admin)):
    find(db, Produto, id)
    db.execute(
        update(Produto)
        .where(Produto.id == id)
        .values(ativo=False, version=Produto.version + 1)
    )
    db.commit()


# Resource factories give employees/finance the same validated CRUD contract.
def register_crud(path, model, schema):
    def index(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        sort: str = "id",
        direction: str = Query("desc", pattern="^(asc|desc)$"),
        q: str = Query("", max_length=200),
        db: Session = Depends(get_db),
        user=Depends(admin),
    ):
        return listing(db, model, page, page_size, sort, direction, q)

    def get(id: int, db: Session = Depends(get_db), user=Depends(admin)):
        return serialize(find(db, model, id))

    def create(payload: schema, db: Session = Depends(get_db), user=Depends(admin)):
        return persist(db, model(**payload.model_dump()))

    def edit(
        id: int, payload: schema, db: Session = Depends(get_db), user=Depends(admin)
    ):
        row = find(db, model, id)
        for key, value in payload.model_dump().items():
            setattr(row, key, value)
        if model is Funcionario and row.usuario:
            row.usuario.ativo = row.ativo
            if not row.ativo:
                db.query(LoginSession).filter_by(user_id=row.usuario.id).delete()
        return persist(db, row)

    def delete(id: int, db: Session = Depends(get_db), user=Depends(admin)):
        row = find(db, model, id)
        if model is Funcionario:
            row.ativo = False
            if row.usuario:
                row.usuario.ativo = False
                db.query(LoginSession).filter_by(user_id=row.usuario.id).delete()
            persist(db, row)
        else:
            db.delete(row)
            db.commit()

    app.add_api_route(path, index, methods=["GET"], name=f"list_{model.__tablename__}")
    app.add_api_route(
        path + "/{id}", get, methods=["GET"], name=f"get_{model.__tablename__}"
    )
    app.add_api_route(
        path,
        create,
        methods=["POST"],
        status_code=201,
        name=f"create_{model.__tablename__}",
    )
    app.add_api_route(
        path + "/{id}", edit, methods=["PUT"], name=f"edit_{model.__tablename__}"
    )
    app.add_api_route(
        path + "/{id}",
        delete,
        methods=["DELETE"],
        status_code=204,
        name=f"delete_{model.__tablename__}",
    )


register_crud("/api/employees", Funcionario, Employee)
register_crud("/api/transactions", Transacao, Transaction)


def register_movements(path, model, schema, kind):
    def index(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        sort: str = "id",
        direction: str = Query("desc", pattern="^(asc|desc)$"),
        q: str = Query("", max_length=200),
        db: Session = Depends(get_db),
        user=Depends(admin if kind == "purchase" else current_user),
    ):
        return listing(db, model, page, page_size, sort, direction, q)

    def get(
        id: int,
        db: Session = Depends(get_db),
        user=Depends(admin if kind == "purchase" else current_user),
    ):
        return serialize(find(db, model, id))

    def create(
        payload: schema,
        db: Session = Depends(get_db),
        user=Depends(admin if kind == "purchase" else current_user),
    ):
        values = payload.model_dump(exclude_none=True)
        values["data_compra" if kind == "purchase" else "data_venda"] = values.pop(
            "data"
        )
        if kind == "purchase":
            row = CompraService.criar_compra(db, **values)
        else:
            row = VendaService.criar_venda(
                db, **values, funcionario_id=user.funcionario_id
            )
        return serialize(row)

    def delete(id: int, db: Session = Depends(get_db), user=Depends(admin)):
        fn = (
            CompraService.cancelar_compra
            if kind == "purchase"
            else VendaService.cancelar_venda
        )
        if not fn(db, id):
            raise HTTPException(404, "Registro não encontrado.")

    app.add_api_route(path, index, methods=["GET"], name=f"list_{model.__tablename__}")
    app.add_api_route(
        path + "/{id}", get, methods=["GET"], name=f"get_{model.__tablename__}"
    )
    app.add_api_route(
        path,
        create,
        methods=["POST"],
        status_code=201,
        name=f"create_{model.__tablename__}",
    )
    app.add_api_route(
        path + "/{id}",
        delete,
        methods=["DELETE"],
        status_code=204,
        name=f"cancel_{model.__tablename__}",
    )


register_movements("/api/sales", Venda, Movement, "sale")
register_movements("/api/purchases", Compra, Purchase, "purchase")


@app.get("/api/dashboard")
def dashboard(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    end = end or business_today()
    start = start or end.replace(day=1)
    if start > end or (end - start).days >= 366:
        raise HTTPException(
            422, "Selecione um período de até 366 dias, em ordem cronológica."
        )
    sales = (
        db.query(Venda.data, func.sum(Venda.valor_total), func.count(Venda.id))
        .filter(Venda.data.between(start, end))
        .group_by(Venda.data)
        .order_by(Venda.data)
        .all()
    )
    daily = {r[0]: (float(r[1]), r[2]) for r in sales}
    series = [
        {
            "data": (start + timedelta(days=i)).isoformat(),
            "total": daily.get(start + timedelta(days=i), (0, 0))[0],
        }
        for i in range((end - start).days + 1)
    ]
    revenue = sum(r["total"] for r in series)
    count = sum(r[2] for r in sales)
    low = (
        db.query(Produto)
        .filter(
            Produto.ativo.is_(True), Produto.estoque_atual <= Produto.estoque_minimo
        )
        .order_by(Produto.estoque_atual, Produto.nome)
        .all()
    )
    purchases = float(
        db.query(func.coalesce(func.sum(Compra.valor_total), 0))
        .filter(Compra.data.between(start, end))
        .scalar()
    )
    entries = float(
        db.query(func.coalesce(func.sum(Transacao.valor), 0))
        .filter(Transacao.data.between(start, end), Transacao.tipo == "entrada")
        .scalar()
    )
    exits = float(
        db.query(func.coalesce(func.sum(Transacao.valor), 0))
        .filter(Transacao.data.between(start, end), Transacao.tipo == "saída")
        .scalar()
    )
    payments = (
        db.query(Venda.metodo_pagamento, func.sum(Venda.valor_total))
        .filter(Venda.data.between(start, end))
        .group_by(Venda.metodo_pagamento)
        .all()
    )
    result = {
        "revenue": revenue,
        "sales_count": count,
        "ticket": revenue / count if count else 0,
        "products_count": db.query(Produto).filter(Produto.ativo.is_(True)).count(),
        "low_stock": [serialize(p) for p in low],
        "series": series,
        "payments": [{"name": p[0], "total": float(p[1])} for p in payments],
    }
    if user.nivel_acesso == "admin":
        result.update(
            purchases=purchases, cash_balance=revenue + entries - purchases - exits
        )
    return result


app.mount("/assets", StaticFiles(directory=WEB), name="assets")


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(WEB / "index.html")
