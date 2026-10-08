"""Firestore infrastructure.

The FastAPI server uses the Firebase Admin SDK. Browser clients never receive
a service-account key and cannot address Firestore directly.
"""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import Any

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1 import Client

COLLECTIONS = ("users", "employees", "products", "sales", "purchases", "transactions")


@lru_cache(maxsize=1)
def get_firestore() -> Client:
    """Initialize lazily, allowing the test suite to run against the emulator."""
    project = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    if not project and os.getenv("FIRESTORE_EMULATOR_HOST"):
        project = "demo-coffee-bi"
    if not project:
        raise RuntimeError(
            "Configure FIREBASE_PROJECT_ID e GOOGLE_APPLICATION_CREDENTIALS "
            "ou credenciais padrão da plataforma. Não foi configurado um banco Firebase."
        )
    try:
        app = firebase_admin.get_app()
    except ValueError:
        # Uses Application Default Credentials on servers; emulator is recognized
        # automatically by the Firestore client when FIRESTORE_EMULATOR_HOST is set.
        app = firebase_admin.initialize_app(options={"projectId": project})
    return firestore.client(app=app)


def ref(db: Client, collection: str, ident: int | str):
    if collection not in COLLECTIONS:
        raise ValueError("Coleção não permitida")
    return db.collection(collection).document(str(ident))


def username_key(username: str) -> str:
    canonical = username.strip().casefold()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def user_lookup_ref(db: Client, username: str):
    return db.collection("usernames").document(username_key(username))


def next_id_in_transaction(db: Client, transaction, collection: str) -> tuple[int, Any]:
    """Read the counter BEFORE the first transaction write."""
    if collection not in COLLECTIONS:
        raise ValueError("Coleção não permitida")
    counter = db.collection("_counters").document(collection)
    snapshot = counter.get(transaction=transaction)
    return int((snapshot.to_dict() or {}).get("next", 1)), counter


def record(snapshot) -> dict | None:
    if not snapshot.exists:
        return None
    return {"id": int(snapshot.id), **(snapshot.to_dict() or {})}


def all_records(db: Client, collection: str, *, limit: int = 500) -> list[dict]:
    if collection not in COLLECTIONS:
        raise ValueError("Coleção não permitida")
    rows = [record(s) for s in db.collection(collection).limit(limit).stream()]
    return [r for r in rows if r is not None]


def cents(value) -> int:
    from decimal import Decimal, ROUND_HALF_UP
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def reais(value) -> float:
    return int(value or 0) / 100.0
