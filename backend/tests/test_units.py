"""Pure functions and validation: no database needed."""
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas import BudgetIn, TransactionIn, UserCreate
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.serializers import month_range, to_utc_datetime

pytestmark = pytest.mark.no_db

TX = dict(title="x", amount=1, type="expense", category="Food", date="2026-11-24")


def test_password_hashing_uses_argon2():
    h = hash_password("s3cret-pass")
    assert h.startswith("$argon2id$")
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)
    assert not verify_password("anything", None)


def test_jwt_round_trip_and_tampering():
    token = create_access_token("507f1f77bcf86cd799439011", version=3)
    claims = decode_access_token(token)
    assert claims.user_id == "507f1f77bcf86cd799439011" and claims.version == 3
    assert decode_access_token(token + "x") is None
    assert decode_access_token("garbage") is None


@pytest.mark.parametrize(
    "year, month, start, end",
    [
        (2026, 11, datetime(2026, 11, 1), datetime(2026, 12, 1)),
        (2026, 12, datetime(2026, 12, 1), datetime(2027, 1, 1)),
        (2028, 2, datetime(2028, 2, 1), datetime(2028, 3, 1)),
    ],
)
def test_month_range(year, month, start, end):
    assert month_range(year, month) == (start.replace(tzinfo=timezone.utc), end.replace(tzinfo=timezone.utc))


def test_to_utc_datetime_is_midnight_utc():
    assert to_utc_datetime(date(2026, 11, 24)) == datetime(2026, 11, 24, tzinfo=timezone.utc)


def test_transaction_input_is_cleaned():
    t = TransactionIn(title="  Lunch ", amount=250.456, type="expense", category="Food", date="2026-11-24")
    assert t.title == "Lunch"
    assert t.amount == 250.46
    assert t.date == date(2026, 11, 24)
    assert t.description == ""


@pytest.mark.parametrize("bad", [dict(amount=0), dict(amount=-5), dict(type="transfer"), dict(title="  ")])
def test_transaction_input_rejects(bad):
    with pytest.raises(ValidationError):
        TransactionIn(**{**TX, **bad})


def test_budget_month_must_be_1_to_12():
    with pytest.raises(ValidationError):
        BudgetIn(category="Food", monthly_limit=5000, month=13, year=2026)


def test_user_email_is_validated():
    with pytest.raises(ValidationError):
        UserCreate(name="A", email="not-an-email", password="12345678")


def test_protected_routes_need_a_token_before_touching_the_db():
    client = TestClient(app)  # no lifespan: no DB connection
    for path in ["/api/auth/me", "/api/transactions", "/api/categories", "/api/budgets", "/api/analytics/summary"]:
        assert client.get(path).status_code == 401, path
    assert client.get("/api/transactions", headers={"Authorization": "Bearer nonsense"}).status_code == 401
