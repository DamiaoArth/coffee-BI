"""Coffee BI — REST API on Firebase Cloud Firestore.

All mutations go through authenticated FastAPI endpoints; browser clients never
access Firestore directly. Keep front-end JSON contracts compatible with SPA.
"""
from __future__ import annotations

import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from firebase_admin import firestore
from google.cloud.firestore_v1 import Client, Query
from google.cloud.firestore_v1.base_query import FieldFilter
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, Field

from api.firebase_db import (
    all_records, cents, get_firestore, next_id_in_transaction, reais, ref,
    user_lookup_ref,
)
from services.auth_service import AuthService

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
FRONT = ROOT / "web"
PROD = os.getenv("APP_ENV", "development") == "production"
SECRET = os.getenv("SESSION_SECRET") or ""
if PROD and len(SECRET) < 32:
    raise RuntimeError("SESSION_SECRET deve ter no mínimo 32 caracteres na produção.")
if not SECRET:
    SECRET = secrets.token_urlsafe(48)
SIGN = URLSafeTimedSerializer(SECRET, salt="coffee-bi-firebase-v1")
COOKIE = "coffee_session"
TTL = 8 * 3600
BUSINESS_TZ = ZoneInfo(os.getenv("BUSINESS_TIMEZONE", "America/Sao_Paulo"))
attempts: dict[str, deque] = defaultdict(deque)
app = FastAPI(title="Coffee BI API · Firebase", version="2.0",
              docs_url="/api/docs", openapi_url="/api/openapi.json")
DB = Annotated[Client, Depends(get_firestore)]


def business_today() -> date:
    return datetime.now(BUSINESS_TZ).date()


def business_now() -> datetime:
    return datetime.now(BUSINESS_TZ)


@app.on_event("startup")
def startup():
    # Fail fast: no local SQLite fallback if Firebase credentials are absent.
    get_firestore()


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = (
        "no-store" if request.url.path.startswith("/api/") else "no-cache"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    return response


def session_info(request: Request) -> dict:
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise HTTPException(401, "Faça login para continuar.")
    try:
        return SIGN.loads(raw, max_age=TTL)
    except (BadSignature, SignatureExpired, ValueError):
        raise HTTPException(401, "Sessão expirada. Entre novamente.")


def public_user(user: dict) -> dict:
    return {
        "id": int(user["id"]), "username": user["nome_usuario"],
        "role": user["nivel_acesso"], "funcionario_id": user.get("funcionario_id"),
    }


def current_user(request: Request, db: DB) -> dict:
    sess = session_info(request)
    try:
        u = ref(db, "users", int(sess["uid"])).get()
    except (KeyError, TypeError, ValueError):
        raise HTTPException(401, "Sessão inválida.")
    if not u.exists or not u.to_dict().get("ativo", False):
        raise HTTPException(401, "Conta inativa ou sessão inválida.")
    user = {"id": int(u.id), **u.to_dict()}
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        allowed = {str(request.base_url).rstrip("/")}
        public = os.getenv("PUBLIC_ORIGIN", "").rstrip("/")
        if public:
            allowed.add(public)
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in allowed:
            raise HTTPException(403, "Origem não autorizada.")
        expected = hmac.new(
            SECRET.encode(), sess["nonce"].encode(), "sha256"
        ).hexdigest()
        if not hmac.compare_digest(
            request.headers.get("x-csrf-token", ""), expected
        ):
            raise HTTPException(403, "Token CSRF ausente ou inválido.")
    return user


User = Annotated[dict, Depends(current_user)]


def management(user: User) -> dict:
    if user["nivel_acesso"] not in ("admin", "Gerente"):
        raise HTTPException(403, "Operação restrita à gestão.")
    return user


Manager = Annotated[dict, Depends(management)]


def administrator(user: User) -> dict:
    if user["nivel_acesso"] != "admin":
        raise HTTPException(403, "Apenas administradores podem executar esta operação.")
    return user


Admin = Annotated[dict, Depends(administrator)]


def product_json(obj: dict) -> dict:
    return {
        "id": obj["id"], "nome": obj["nome"], "categoria": obj["categoria"],
        "preco_venda": reais(obj["preco_venda_centavos"]),
        "custo_unitario": reais(obj["custo_unitario_centavos"]),
        "estoque_atual": obj["estoque_atual"], "estoque_minimo": obj["estoque_minimo"],
        "unidade": obj["unidade"], "ativo": obj.get("ativo", True),
    }


def sale_json(obj: dict) -> dict:
    return {
        "id": obj["id"], "data": obj["data"], "hora": obj["hora"],
        "valor_total": reais(obj["valor_total_centavos"]),
        "metodo_pagamento": obj["metodo_pagamento"],
        "observacoes": obj.get("observacoes"),
        "itens": [
            {
                "id_produto": x["id_produto"], "nome": x["nome"],
                "quantidade": x["quantidade"],
                "preco_unitario": reais(x["preco_unitario_centavos"]),
                "subtotal": reais(x["subtotal_centavos"]),
            }
            for x in obj.get("itens", [])
        ],
    }


def purchase_json(obj: dict) -> dict:
    return {
        "id": obj["id"], "data": obj["data"], "fornecedor": obj["fornecedor"],
        "metodo_pagamento": obj["metodo_pagamento"],
        "valor_total": reais(obj["valor_total_centavos"]),
        "observacoes": obj.get("observacoes"),
        "itens": [
            {
                "id_produto": x["id_produto"], "nome": x["nome"],
                "quantidade": x["quantidade"],
                "preco_unitario": reais(x["preco_unitario_centavos"]),
                "subtotal": reais(x["subtotal_centavos"]),
            }
            for x in obj.get("itens", [])
        ],
    }


def employee_json(obj: dict) -> dict:
    return {key: obj.get(key) for key in (
        "id", "nome", "cargo", "telefone", "email", "ativo", "data_admissao"
    )}


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
    preco_unitario: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )


class SaleInput(BaseModel):
    data: date = Field(default_factory=business_today)
    metodo_pagamento: str = Field(min_length=2, max_length=50)
    observacoes: str | None = Field(default=None, max_length=1000)
    itens: list[LineItem] = Field(min_length=1, max_length=100)


class PurchaseInput(SaleInput):
    fornecedor: str = Field(min_length=2, max_length=200)


class TransactionInput(BaseModel):
    tipo: Literal["entrada", "saída"]
    descricao: str = Field(min_length=2, max_length=200)
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    data: date = Field(default_factory=business_today)
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
def health(db: DB):
    # Explicitly exercise Firestore connectivity, not just process liveness.
    db.collection("_health").document("check").get()
    return {"status": "ok", "database": "firestore"}


@app.post("/api/auth/login")
def login(body: Login, request: Request, response: Response, db: DB):
    key = f"{request.client.host if request.client else 'unknown'}:{body.username.casefold()}"
    q = attempts[key]
    now = time.monotonic()
    while q and now - q[0] > 900:
        q.popleft()
    if len(q) >= 6:
        raise HTTPException(429, "Muitas tentativas. Tente novamente em 15 minutos.")
    index = user_lookup_ref(db, body.username).get()
    user = None
    if index.exists:
        snap = ref(db, "users", index.to_dict()["user_id"]).get()
        if snap.exists:
            user = {"id": int(snap.id), **snap.to_dict()}
    # Equal error whether name exists or password is invalid.
    if not user or not user.get("ativo") or not AuthService.verify_password(
        body.password, user["senha_hash"]
    ):
        q.append(now)
        raise HTTPException(401, "Usuário ou senha inválidos.")
    q.clear()
    nonce = secrets.token_hex(20)
    response.set_cookie(
        COOKIE, SIGN.dumps({"uid": user["id"], "nonce": nonce}),
        max_age=TTL, httponly=True, secure=PROD, samesite="lax", path="/",
    )
    csrf = hmac.new(SECRET.encode(), nonce.encode(), "sha256").hexdigest()
    return {"user": public_user(user), "csrf": csrf}


@app.get("/api/auth/me")
def me(request: Request, user: User):
    sess = session_info(request)
    csrf = hmac.new(SECRET.encode(), sess["nonce"].encode(), "sha256").hexdigest()
    return {"user": public_user(user), "csrf": csrf}


@app.post("/api/auth/logout")
def logout(response: Response, user: User):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


def product_payload(data: ProductInput) -> dict:
    return {
        "nome": data.nome.strip(), "categoria": data.categoria.strip(),
        "preco_venda_centavos": cents(data.preco_venda),
        "custo_unitario_centavos": cents(data.custo_unitario),
        "estoque_atual": data.estoque_atual, "estoque_minimo": data.estoque_minimo,
        "unidade": data.unidade, "ativo": True,
    }


@app.get("/api/products")
def products(db: DB, user: User, all: bool = False):
    rows = all_records(db, "products", limit=2000)
    if not all:
        rows = [x for x in rows if x.get("ativo", True)]
    return [product_json(x) for x in sorted(rows, key=lambda x: x["nome"].casefold())[:1000]]


@app.post("/api/products", status_code=201)
def add_product(data: ProductInput, db: DB, user: Manager):
    tx = db.transaction()
    @firestore.transactional
    def create(transaction):
        next_id, counter = next_id_in_transaction(db, transaction, "products")
        obj = {"id": next_id, **product_payload(data)}
        transaction.set(ref(db, "products", next_id), obj)
        transaction.set(counter, {"next": next_id + 1})
        return obj
    return product_json(create(tx))


@app.put("/api/products/{pid}")
def edit_product(pid: int, data: ProductInput, db: DB, user: Manager):
    tx = db.transaction()
    @firestore.transactional
    def change(transaction):
        document = ref(db, "products", pid)
        snap = document.get(transaction=transaction)
        if not snap.exists:
            raise HTTPException(404, "Produto não encontrado.")
        obj = {"id": pid, **product_payload(data)}
        transaction.update(document, product_payload(data))
        return obj
    return product_json(change(tx))


@app.delete("/api/products/{pid}")
def archive_product(pid: int, db: DB, user: Manager):
    doc = ref(db, "products", pid)
    if not doc.get().exists:
        raise HTTPException(404, "Produto não encontrado.")
    doc.update({"ativo": False})
    return {"ok": True}


@app.get("/api/sales")
def sales(db: DB, user: User):
    rows = all_records(db, "sales", limit=3000)
    return [
        sale_json(s) for s in sorted(
            rows, key=lambda x: (x["data"], int(x["id"])), reverse=True
        )[:300]
    ]


def summed_quantities(lines):
    grouped = {}
    for line in lines:
        grouped[line.id_produto] = grouped.get(line.id_produto, 0) + line.quantidade
    return grouped


@app.post("/api/sales", status_code=201)
def add_sale(data: SaleInput, db: DB, user: User):
    grouped = summed_quantities(data.itens)
    if any(quantity > 100000 for quantity in grouped.values()):
        raise HTTPException(422, "Quantidade total inválida.")
    tx = db.transaction()
    @firestore.transactional
    def create(transaction):
        sale_id, counter = next_id_in_transaction(db, transaction, "sales")
        docs = {pid: ref(db, "products", pid) for pid in grouped}
        # All reads MUST precede all writes. Firestore retries concurrent updates.
        snapshots = {
            pid: doc.get(transaction=transaction) for pid, doc in docs.items()
        }
        products_data = {}
        for pid, snapshot in snapshots.items():
            if not snapshot.exists or not snapshot.to_dict().get("ativo", True):
                raise HTTPException(422, f"Produto {pid} indisponível.")
            product = snapshot.to_dict()
            if product["estoque_atual"] < grouped[pid]:
                raise HTTPException(409, f"Estoque insuficiente: {product['nome']}.")
            products_data[pid] = product
        lines = []
        total = 0
        for pid, quantity in grouped.items():
            p = products_data[pid]
            price = p["preco_venda_centavos"]
            subtotal = price * quantity
            total += subtotal
            lines.append({
                "id_produto": pid, "nome": p["nome"], "quantidade": quantity,
                "preco_unitario_centavos": price, "subtotal_centavos": subtotal,
            })
        sale = {
            "id": sale_id, "data": data.data.isoformat(),
            "hora": business_now().strftime("%H:%M"), "valor_total_centavos": total,
            "metodo_pagamento": data.metodo_pagamento,
            "observacoes": data.observacoes, "funcionario_id": user.get("funcionario_id"),
            "itens": lines,
        }
        for pid, product in products_data.items():
            transaction.update(docs[pid], {
                "estoque_atual": product["estoque_atual"] - grouped[pid]
            })
        transaction.set(ref(db, "sales", sale_id), sale)
        transaction.set(counter, {"next": sale_id + 1})
        return {"id": sale_id, "valor_total": reais(total)}
    return create(tx)


@app.get("/api/purchases")
def purchases(db: DB, user: Manager):
    rows = all_records(db, "purchases", limit=3000)
    return [purchase_json(c) for c in sorted(
        rows, key=lambda x: (x["data"], int(x["id"])), reverse=True
    )[:300]]


@app.post("/api/purchases", status_code=201)
def add_purchase(data: PurchaseInput, db: DB, user: Manager):
    if any(item.preco_unitario is None for item in data.itens):
        raise HTTPException(422, "Informe o custo de cada produto comprado.")
    tx = db.transaction()
    @firestore.transactional
    def create(transaction):
        purchase_id, counter = next_id_in_transaction(db, transaction, "purchases")
        docs = {item.id_produto: ref(db, "products", item.id_produto) for item in data.itens}
        snapshots = {pid: doc.get(transaction=transaction) for pid, doc in docs.items()}
        original = {}
        for pid, snapshot in snapshots.items():
            if not snapshot.exists or not snapshot.to_dict().get("ativo", True):
                raise HTTPException(422, f"Produto {pid} indisponível.")
            original[pid] = snapshot.to_dict()
        lines = []
        total = 0
        additions = {}
        costs = {}
        for item in data.itens:
            cost = cents(item.preco_unitario)
            subtotal = cost * item.quantidade
            total += subtotal
            p = original[item.id_produto]
            lines.append({
                "id_produto": item.id_produto, "nome": p["nome"],
                "quantidade": item.quantidade, "preco_unitario_centavos": cost,
                "subtotal_centavos": subtotal,
            })
            additions[item.id_produto] = additions.get(item.id_produto, 0) + item.quantidade
            costs[item.id_produto] = costs.get(item.id_produto, 0) + subtotal
        for pid, added in additions.items():
            p = original[pid]
            old = p["estoque_atual"]
            new_cost = (p["custo_unitario_centavos"] * old + costs[pid]) // (old + added)
            transaction.update(docs[pid], {
                "estoque_atual": old + added,
                "custo_unitario_centavos": new_cost,
            })
        purchase = {
            "id": purchase_id, "data": data.data.isoformat(), "fornecedor": data.fornecedor,
            "metodo_pagamento": data.metodo_pagamento,
            "observacoes": data.observacoes, "valor_total_centavos": total,
            "itens": lines,
        }
        transaction.set(ref(db, "purchases", purchase_id), purchase)
        transaction.set(counter, {"next": purchase_id + 1})
        return {"id": purchase_id, "valor_total": reais(total)}
    return create(tx)


@app.get("/api/transactions")
def transactions(db: DB, user: Manager):
    rows = all_records(db, "transactions", limit=3000)
    return [{
        "id": x["id"], "tipo": x["tipo"], "descricao": x["descricao"],
        "categoria": x["categoria"], "valor": reais(x["valor_centavos"]),
        "data": x["data"],
    } for x in sorted(rows, key=lambda x: (x["data"], int(x["id"])), reverse=True)[:500]]


@app.post("/api/transactions", status_code=201)
def add_transaction(data: TransactionInput, db: DB, user: Manager):
    tx = db.transaction()
    @firestore.transactional
    def create(transaction):
        ident, counter = next_id_in_transaction(db, transaction, "transactions")
        transaction.set(ref(db, "transactions", ident), {
            "id": ident, "tipo": data.tipo, "descricao": data.descricao,
            "categoria": data.categoria, "valor_centavos": cents(data.valor),
            "data": data.data.isoformat(),
        })
        transaction.set(counter, {"next": ident + 1})
        return {"id": ident}
    return create(tx)


@app.delete("/api/transactions/{tid}")
def delete_transaction(tid: int, db: DB, user: Manager):
    document = ref(db, "transactions", tid)
    if not document.get().exists:
        raise HTTPException(404, "Lançamento não encontrado.")
    document.delete()
    return {"ok": True}


@app.get("/api/employees")
def employees(db: DB, user: Admin):
    rows = all_records(db, "employees", limit=2000)
    return [employee_json(x) for x in sorted(rows, key=lambda x: x["nome"].casefold())]


@app.post("/api/employees", status_code=201)
def add_employee(data: EmployeeInput, db: DB, user: Admin):
    tx = db.transaction()
    @firestore.transactional
    def create(transaction):
        ident, counter = next_id_in_transaction(db, transaction, "employees")
        obj = {"id": ident, **data.model_dump(), "data_admissao": business_today().isoformat()}
        transaction.set(ref(db, "employees", ident), obj)
        transaction.set(counter, {"next": ident + 1})
        return obj
    return employee_json(create(tx))


@app.put("/api/employees/{eid}")
def edit_employee(eid: int, data: EmployeeInput, db: DB, user: Admin):
    doc = ref(db, "employees", eid)
    old = doc.get()
    if not old.exists:
        raise HTTPException(404, "Funcionário não encontrado.")
    obj = {**old.to_dict(), **data.model_dump(), "id": eid}
    doc.update(data.model_dump())
    return employee_json(obj)


@app.get("/api/users")
def users(db: DB, user: Admin):
    return [public_user(x) | {"ativo": x.get("ativo", True)}
            for x in all_records(db, "users", limit=1000)]


def register_user(db: Client, *, username: str, password_hash: str,
                  role: str, employee_id: int | None = None) -> dict:
    username = username.strip()
    if not username:
        raise HTTPException(422, "Nome de usuário inválido.")
    tx = db.transaction()
    @firestore.transactional
    def create(transaction):
        index_doc = user_lookup_ref(db, username)
        index = index_doc.get(transaction=transaction)
        next_id, counter = next_id_in_transaction(db, transaction, "users")
        employee = ref(db, "employees", employee_id).get(transaction=transaction) if employee_id else None
        if index.exists:
            raise HTTPException(409, "Nome de usuário já cadastrado.")
        if employee_id and (not employee or not employee.exists):
            raise HTTPException(422, "Funcionário não encontrado.")
        # An employee cannot have two user accounts.
        if employee_id:
            existing = list(db.collection("users").where(
                filter=FieldFilter("funcionario_id", "==", employee_id)
            ).stream(transaction=transaction))
            if existing:
                raise HTTPException(409, "Funcionário já possui acesso.")
        obj = {
            "id": next_id, "nome_usuario": username, "senha_hash": password_hash,
            "nivel_acesso": role, "funcionario_id": employee_id, "ativo": True,
        }
        transaction.set(ref(db, "users", next_id), obj)
        transaction.set(index_doc, {"user_id": next_id, "nome_usuario": username})
        transaction.set(counter, {"next": next_id + 1})
        return obj
    return create(tx)


@app.post("/api/users", status_code=201)
def add_user(data: NewUser, db: DB, user: Admin):
    obj = register_user(
        db, username=data.nome_usuario, password_hash=AuthService.hash_password(data.senha),
        role=data.nivel_acesso, employee_id=data.funcionario_id,
    )
    return public_user(obj)


def period_rows(db: Client, collection: str, begin: str, end: str) -> list[dict]:
    # A single-field range query uses Firestore's default indexes. No compound index
    # is required; bounded to 365 days by the API.
    query = db.collection(collection).where(filter=FieldFilter("data", ">=", begin))
    return [snapshot.to_dict() for snapshot in query.stream()
            if (snapshot.to_dict() or {}).get("data", "") <= end]


def build_dashboard(db: Client, days: int) -> dict:
    days = min(max(days, 1), 365)
    today = business_today()
    first = today - timedelta(days=days - 1)
    sales_rows = period_rows(db, "sales", first.isoformat(), today.isoformat())
    purchase_rows = period_rows(db, "purchases", first.isoformat(), today.isoformat())
    sales_total = sum(x["valor_total_centavos"] for x in sales_rows)
    purchased_total = sum(x["valor_total_centavos"] for x in purchase_rows)
    today_total = sum(x["valor_total_centavos"] for x in sales_rows
                      if x["data"] == today.isoformat())
    products_rows = all_records(db, "products", limit=2000)
    active = [p for p in products_rows if p.get("ativo", True)]
    low = sorted(
        (p for p in active if p["estoque_atual"] <= p["estoque_minimo"]),
        key=lambda p: p["estoque_atual"],
    )[:10]
    days_map: dict[str, int] = {}
    tops: dict[str, int] = {}
    payments: dict[str, int] = {}
    for sale in sales_rows:
        days_map[sale["data"]] = days_map.get(sale["data"], 0) + sale["valor_total_centavos"]
        method = sale["metodo_pagamento"]
        payments[method] = payments.get(method, 0) + sale["valor_total_centavos"]
        for line in sale.get("itens", []):
            name = line.get("nome", "Produto")
            tops[name] = tops.get(name, 0) + int(line["quantidade"])
    return {
        "periodo": days, "faturamento": reais(sales_total),
        "vendas": len(sales_rows),
        "ticket_medio": reais(sales_total // len(sales_rows)) if sales_rows else 0,
        "vendas_hoje": reais(today_total),
        "produtos_ativos": len(active), "estoque_baixo": [product_json(p) for p in low],
        "compras": reais(purchased_total),
        "serie": [{"data": d, "total": reais(v)} for d, v in sorted(days_map.items())],
        "top_produtos": [
            {"nome": name, "quantidade": quantity}
            for name, quantity in sorted(tops.items(), key=lambda x: x[1], reverse=True)[:5]
        ],
        "pagamentos": [{"nome": name, "total": reais(value)}
                       for name, value in sorted(payments.items(), key=lambda x: x[1], reverse=True)],
    }


@app.get("/api/dashboard")
def dashboard(db: DB, user: User, days: int = 30):
    return build_dashboard(db, days)


@app.get("/api/bi")
def bi(db: DB, user: Manager, days: int = 30):
    metrics = build_dashboard(db, days)
    first = business_today() - timedelta(days=min(max(days, 1), 365) - 1)
    rows = period_rows(db, "transactions", first.isoformat(), business_today().isoformat())
    inc = sum(t["valor_centavos"] for t in rows if t["tipo"] == "entrada")
    out = sum(t["valor_centavos"] for t in rows if t["tipo"] == "saída")
    metrics.update({
        "entradas": reais(inc), "saidas": reais(out),
        "saldo_operacional": reais(
            cents(Decimal(str(metrics["faturamento"])))
            - cents(Decimal(str(metrics["compras"]))) + inc - out
        ),
    })
    return metrics


@app.get("/styles.css", include_in_schema=False)
def css():
    return FileResponse(FRONT / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def javascript():
    return FileResponse(FRONT / "app.js", media_type="application/javascript")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/") or "." in path:
        raise HTTPException(404, "Recurso inexistente.")
    return FileResponse(FRONT / "index.html")
