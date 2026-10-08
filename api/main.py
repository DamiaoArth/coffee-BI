"""Coffee BI: FastAPI backend sobre o banco SQLAlchemy original."""
from __future__ import annotations
import hmac
import logging
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, Field
from sqlalchemy import func, update
from sqlalchemy.orm import Session, selectinload

from config.database import SessionLocal, init_db
from models.database_models import Compra, Funcionario, ItemCompra, ItemVenda, Produto, Transacao, Usuario, Venda
from services.auth_service import AuthService

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
FRONT = ROOT / "web"
PROD = os.getenv("APP_ENV", "development") == "production"
SECRET = os.getenv("SESSION_SECRET", "")
if PROD and len(SECRET) < 32:
    raise RuntimeError("SESSION_SECRET deve ter ao menos 32 caracteres em produção.")
if not SECRET:
    SECRET = secrets.token_urlsafe(48)
    logging.warning("SESSION_SECRET temporária: sessões não sobreviverão a reinicializações.")
SIGN = URLSafeTimedSerializer(SECRET, salt="coffee-bi-v1")
COOKIE = "coffee_session"
TTL = 8 * 3600
attempts: dict[str, deque] = defaultdict(deque)
app = FastAPI(title="Coffee BI API", version="1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

@app.on_event("startup")
def start():
    init_db()

@app.middleware("http")
async def headers(request: Request, call_next):
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    r.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
    r.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    return r

def db_session():
    with SessionLocal() as session:
        yield session

DB = Annotated[Session, Depends(db_session)]

def auth_session(request: Request) -> dict:
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise HTTPException(401, "Faça login para continuar.")
    try:
        return SIGN.loads(raw, max_age=TTL)
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "Sessão expirada. Faça login novamente.")

def current_user(request: Request, db: DB) -> Usuario:
    sess = auth_session(request)
    user = db.get(Usuario, sess.get("uid"))
    if user is None or not user.ativo:
        raise HTTPException(401, "Conta inativa ou sessão inválida.")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        allowed = {str(request.base_url).rstrip("/")}
        public = os.getenv("PUBLIC_ORIGIN", "").rstrip("/")
        if public:
            allowed.add(public)
        if origin and origin.rstrip("/") not in allowed:
            raise HTTPException(403, "Origem não autorizada.")
        expected = hmac.new(SECRET.encode(), sess["nonce"].encode(), "sha256").hexdigest()
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), expected):
            raise HTTPException(403, "Token CSRF inválido.")
    return user

User = Annotated[Usuario, Depends(current_user)]

def management(user: User) -> Usuario:
    if user.nivel_acesso not in ("admin", "Gerente"):
        raise HTTPException(403, "Operação restrita à gestão.")
    return user

Manager = Annotated[Usuario, Depends(management)]

def administrator(user: User) -> Usuario:
    if user.nivel_acesso != "admin":
        raise HTTPException(403, "Apenas administradores podem executar esta operação.")
    return user

Admin = Annotated[Usuario, Depends(administrator)]

def money(v) -> float:
    return float(v or 0)

def user_json(u: Usuario) -> dict:
    return {"id": u.id, "username": u.nome_usuario, "role": u.nivel_acesso, "funcionario_id": u.funcionario_id}

def product_json(p: Produto) -> dict:
    return {"id": p.id, "nome": p.nome, "categoria": p.categoria, "preco_venda": money(p.preco_venda),
            "custo_unitario": money(p.custo_unitario), "estoque_atual": p.estoque_atual,
            "estoque_minimo": p.estoque_minimo, "unidade": p.unidade, "ativo": p.ativo}

def sale_json(v: Venda) -> dict:
    return {"id": v.id, "data": str(v.data), "hora": str(v.hora or "")[:5],
            "valor_total": money(v.valor_total), "metodo_pagamento": v.metodo_pagamento,
            "observacoes": v.observacoes, "itens": [
                {"id_produto": x.id_produto, "nome": x.produto.nome if x.produto else "Produto",
                 "quantidade": x.quantidade, "preco_unitario": money(x.preco_unitario),
                 "subtotal": money(x.subtotal)} for x in v.itens]}

def purchase_json(c: Compra) -> dict:
    return {"id": c.id, "data": str(c.data), "fornecedor": c.fornecedor,
            "metodo_pagamento": c.metodo_pagamento, "valor_total": money(c.valor_total),
            "itens": [{"id_produto": x.id_produto, "nome": x.produto.nome if x.produto else "Produto",
                       "quantidade": x.quantidade, "preco_unitario": money(x.preco_unitario)} for x in c.itens]}

def employee_json(f: Funcionario) -> dict:
    return {"id": f.id, "nome": f.nome, "cargo": f.cargo, "telefone": f.telefone,
            "email": f.email, "ativo": f.ativo, "data_admissao": str(f.data_admissao or "")}

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)

class ProductInput(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    categoria: str = Field(min_length=1, max_length=50)
    preco_venda: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    custo_unitario: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    estoque_atual: int = Field(ge=0)
    estoque_minimo: int = Field(ge=0)
    unidade: str = Field(default="un", max_length=10)

class LineItem(BaseModel):
    id_produto: int = Field(gt=0)
    quantidade: int = Field(ge=1, le=100000)
    preco_unitario: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)

class SaleInput(BaseModel):
    data: date = Field(default_factory=date.today)
    metodo_pagamento: str = Field(min_length=2, max_length=50)
    observacoes: str | None = Field(default=None, max_length=1000)
    itens: list[LineItem] = Field(min_length=1, max_length=100)

class PurchaseInput(SaleInput):
    fornecedor: str = Field(min_length=2, max_length=200)

class TransactionInput(BaseModel):
    tipo: Literal["entrada", "saída"]
    descricao: str = Field(min_length=2, max_length=200)
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    data: date = Field(default_factory=date.today)
    categoria: str = Field(min_length=1, max_length=50)

class EmployeeInput(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    cargo: Literal["admin", "Gerente", "funcionario"] = "funcionario"
    email: str | None = Field(default=None, max_length=200)
    telefone: str | None = Field(default=None, max_length=20)
    ativo: bool = True

class NewUser(BaseModel):
    nome_usuario: str = Field(min_length=3, max_length=100)
    senha: str = Field(min_length=10, max_length=256)
    nivel_acesso: Literal["admin", "Gerente", "funcionario"] = "funcionario"
    funcionario_id: int | None = None

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/auth/login")
def login(body: Login, request: Request, response: Response, db: DB):
    key = f"{request.client.host if request.client else 'unknown'}:{body.username.lower()}"
    q = attempts[key]
    now = time.monotonic()
    while q and now - q[0] > 900:
        q.popleft()
    if len(q) >= 6:
        raise HTTPException(429, "Muitas tentativas. Tente novamente em 15 minutos.")
    u = AuthService.authenticate(db, body.username, body.password)
    if not u:
        q.append(now)
        raise HTTPException(401, "Usuário ou senha inválidos.")
    q.clear()
    nonce = secrets.token_hex(20)
    response.set_cookie(COOKIE, SIGN.dumps({"uid": u.id, "nonce": nonce}),
                        max_age=TTL, httponly=True, secure=PROD, samesite="lax", path="/")
    csrf = hmac.new(SECRET.encode(), nonce.encode(), "sha256").hexdigest()
    return {"user": user_json(u), "csrf": csrf}

@app.get("/api/auth/me")
def me(request: Request, user: User):
    sess = auth_session(request)
    return {"user": user_json(user), "csrf": hmac.new(SECRET.encode(), sess["nonce"].encode(), "sha256").hexdigest()}

@app.post("/api/auth/logout")
def logout(response: Response, user: User):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}

@app.get("/api/products")
def products(db: DB, user: User, all: bool = False):
    q = db.query(Produto)
    if not all:
        q = q.filter(Produto.ativo.is_(True))
    return [product_json(p) for p in q.order_by(Produto.nome).limit(1000)]

@app.post("/api/products", status_code=201)
def add_product(data: ProductInput, db: DB, user: Manager):
    p = Produto(**data.model_dump(), ativo=True)
    db.add(p)
    db.commit()
    db.refresh(p)
    return product_json(p)

@app.put("/api/products/{pid}")
def edit_product(pid: int, data: ProductInput, db: DB, user: Manager):
    p = db.get(Produto, pid)
    if not p:
        raise HTTPException(404, "Produto não encontrado.")
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    db.commit()
    return product_json(p)

@app.delete("/api/products/{pid}")
def archive_product(pid: int, db: DB, user: Manager):
    p = db.get(Produto, pid)
    if not p:
        raise HTTPException(404, "Produto não encontrado.")
    p.ativo = False
    db.commit()
    return {"ok": True}

@app.get("/api/sales")
def sales(db: DB, user: User):
    q = db.query(Venda).options(selectinload(Venda.itens).selectinload(ItemVenda.produto))
    return [sale_json(v) for v in q.order_by(Venda.data.desc(), Venda.id.desc()).limit(300)]

@app.post("/api/sales", status_code=201)
def add_sale(data: SaleInput, db: DB, user: User):
    try:
        total = Decimal("0")
        sale = Venda(data=data.data, hora=datetime.now().time(), valor_total=0,
                     metodo_pagamento=data.metodo_pagamento, observacoes=data.observacoes,
                     funcionario_id=user.funcionario_id)
        db.add(sale)
        db.flush()
        for item in data.itens:
            p = db.get(Produto, item.id_produto)
            if not p or not p.ativo:
                raise HTTPException(422, f"Produto {item.id_produto} indisponível.")
            change = db.execute(update(Produto).where(Produto.id == p.id,
                        Produto.estoque_atual >= item.quantidade).values(
                        estoque_atual=Produto.estoque_atual - item.quantidade))
            if change.rowcount != 1:
                raise HTTPException(409, f"Estoque insuficiente: {p.nome}.")
            subtotal = p.preco_venda * item.quantidade
            total += subtotal
            db.add(ItemVenda(id_venda=sale.id, id_produto=p.id, quantidade=item.quantidade,
                             preco_unitario=p.preco_venda, subtotal=subtotal))
        sale.valor_total = total
        db.commit()
        return {"id": sale.id, "valor_total": money(total)}
    except Exception:
        db.rollback()
        raise

@app.get("/api/purchases")
def purchases(db: DB, user: Manager):
    q = db.query(Compra).options(selectinload(Compra.itens).selectinload(ItemCompra.produto))
    return [purchase_json(c) for c in q.order_by(Compra.data.desc(), Compra.id.desc()).limit(300)]

@app.post("/api/purchases", status_code=201)
def add_purchase(data: PurchaseInput, db: DB, user: Manager):
    try:
        total = Decimal("0")
        purchase = Compra(data=data.data, fornecedor=data.fornecedor, metodo_pagamento=data.metodo_pagamento,
                          valor_total=0, observacoes=data.observacoes)
        db.add(purchase)
        db.flush()
        for item in data.itens:
            p = db.get(Produto, item.id_produto)
            if not p or not p.ativo:
                raise HTTPException(422, f"Produto {item.id_produto} indisponível.")
            if item.preco_unitario is None:
                raise HTTPException(422, "Preço de custo obrigatório para compras.")
            old = p.estoque_atual
            p.custo_unitario = (p.custo_unitario * old + item.preco_unitario * item.quantidade) / (old + item.quantidade)
            p.estoque_atual += item.quantidade
            subtotal = item.preco_unitario * item.quantidade
            total += subtotal
            db.add(ItemCompra(id_compra=purchase.id, id_produto=p.id, quantidade=item.quantidade,
                              preco_unitario=item.preco_unitario, subtotal=subtotal))
        purchase.valor_total = total
        db.commit()
        return {"id": purchase.id, "valor_total": money(total)}
    except Exception:
        db.rollback()
        raise

@app.get("/api/transactions")
def transactions(db: DB, user: Manager):
    rows = db.query(Transacao).order_by(Transacao.data.desc(), Transacao.id.desc()).limit(500)
    return [{"id": x.id, "tipo": x.tipo, "descricao": x.descricao, "categoria": x.categoria,
             "valor": money(x.valor), "data": str(x.data)} for x in rows]

@app.post("/api/transactions", status_code=201)
def add_transaction(data: TransactionInput, db: DB, user: Manager):
    obj = Transacao(**data.model_dump())
    db.add(obj)
    db.commit()
    return {"id": obj.id}

@app.delete("/api/transactions/{tid}")
def delete_transaction(tid: int, db: DB, user: Manager):
    obj = db.get(Transacao, tid)
    if not obj:
        raise HTTPException(404, "Lançamento não encontrado.")
    db.delete(obj)
    db.commit()
    return {"ok": True}

@app.get("/api/employees")
def employees(db: DB, user: Admin):
    return [employee_json(f) for f in db.query(Funcionario).order_by(Funcionario.nome)]

@app.post("/api/employees", status_code=201)
def add_employee(data: EmployeeInput, db: DB, user: Admin):
    emp = Funcionario(**data.model_dump(), data_admissao=date.today())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return employee_json(emp)

@app.put("/api/employees/{eid}")
def edit_employee(eid: int, data: EmployeeInput, db: DB, user: Admin):
    emp = db.get(Funcionario, eid)
    if not emp:
        raise HTTPException(404, "Funcionário não encontrado.")
    for k, v in data.model_dump().items():
        setattr(emp, k, v)
    db.commit()
    return employee_json(emp)

@app.get("/api/users")
def users(db: DB, user: Admin):
    return [user_json(u) | {"ativo": u.ativo} for u in db.query(Usuario).all()]

@app.post("/api/users", status_code=201)
def add_user(data: NewUser, db: DB, user: Admin):
    if db.query(Usuario).filter(Usuario.nome_usuario == data.nome_usuario).first():
        raise HTTPException(409, "Nome de usuário já cadastrado.")
    if data.funcionario_id and db.query(Usuario).filter(Usuario.funcionario_id == data.funcionario_id).first():
        raise HTTPException(409, "Funcionário já possui acesso.")
    if data.funcionario_id and not db.get(Funcionario, data.funcionario_id):
        raise HTTPException(422, "Funcionário não encontrado.")
    obj = Usuario(nome_usuario=data.nome_usuario, senha_hash=AuthService.hash_password(data.senha),
                  nivel_acesso=data.nivel_acesso, funcionario_id=data.funcionario_id, ativo=True)
    db.add(obj)
    db.commit()
    return user_json(obj)

@app.get("/api/dashboard")
def dashboard(db: DB, user: User, days: int = 30):
    days = min(max(days, 1), 365)
    today = date.today()
    first = today - timedelta(days=days - 1)
    rows = db.query(Venda).filter(Venda.data >= first, Venda.data <= today).all()
    revenue = sum((v.valor_total for v in rows), Decimal("0"))
    today_revenue = sum((v.valor_total for v in rows if v.data == today), Decimal("0"))
    low = db.query(Produto).filter(Produto.ativo.is_(True),
            Produto.estoque_atual <= Produto.estoque_minimo).order_by(Produto.estoque_atual).limit(10).all()
    active = db.query(func.count(Produto.id)).filter(Produto.ativo.is_(True)).scalar() or 0
    daily = db.query(Venda.data, func.sum(Venda.valor_total)).filter(
        Venda.data >= first, Venda.data <= today).group_by(Venda.data).order_by(Venda.data).all()
    top = db.query(Produto.nome, func.sum(ItemVenda.quantidade)).join(ItemVenda).join(Venda).filter(
        Venda.data >= first, Venda.data <= today).group_by(Produto.id, Produto.nome).order_by(
        func.sum(ItemVenda.quantidade).desc()).limit(5).all()
    methods = db.query(Venda.metodo_pagamento, func.sum(Venda.valor_total)).filter(
        Venda.data >= first, Venda.data <= today).group_by(Venda.metodo_pagamento).all()
    buys = db.query(func.sum(Compra.valor_total)).filter(
        Compra.data >= first, Compra.data <= today).scalar()
    return {"periodo": days, "faturamento": money(revenue), "vendas": len(rows),
            "ticket_medio": money(revenue / len(rows)) if rows else 0,
            "vendas_hoje": money(today_revenue), "produtos_ativos": active,
            "estoque_baixo": [product_json(p) for p in low], "compras": money(buys),
            "serie": [{"data": str(d), "total": money(v)} for d, v in daily],
            "top_produtos": [{"nome": n, "quantidade": int(q)} for n, q in top],
            "pagamentos": [{"nome": n, "total": money(v)} for n, v in methods]}

@app.get("/api/bi")
def bi(db: DB, user: Manager, days: int = 30):
    metrics = dashboard(db=db, user=user, days=days)
    first = date.today() - timedelta(days=min(max(days, 1), 365) - 1)
    transactions = db.query(Transacao).filter(Transacao.data >= first).all()
    incoming = sum((t.valor for t in transactions if t.tipo == "entrada"), Decimal("0"))
    outgoing = sum((t.valor for t in transactions if t.tipo == "saída"), Decimal("0"))
    metrics.update(entradas=money(incoming), saidas=money(outgoing),
                   saldo_operacional=metrics["faturamento"] - metrics["compras"] + money(incoming - outgoing))
    return metrics

@app.get("/styles.css", include_in_schema=False)
def css():
    return FileResponse(FRONT / "styles.css", media_type="text/css")

@app.get("/app.js", include_in_schema=False)
def js():
    return FileResponse(FRONT / "app.js", media_type="application/javascript")

@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/") or "." in path:
        raise HTTPException(404, "Recurso inexistente.")
    return FileResponse(FRONT / "index.html")
