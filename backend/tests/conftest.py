"""Test setup: the API runs against a real MongoDB, in a separate test database.

Start one with `docker compose up mongo` (or set MONGODB_URL). Every collection is
emptied before each test.
"""
import os

# Must be set before the app (and its settings) are imported.
os.environ["MONGODB_DB"] = "expense_tracker_test"
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256-0123456789"
os.environ["RATE_LIMIT_ENABLED"] = "false"  # test_security turns it on for its own test

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.main import app

COLLECTIONS = ("users", "transactions", "categories", "budgets", "goals")


@pytest.fixture(scope="session")
def _sync_db():
    client = MongoClient(os.environ["MONGODB_URL"], serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
    except Exception as exc:  # noqa: BLE001 - any connection failure
        message = f"MongoDB not reachable at {os.environ['MONGODB_URL']} (start it with `docker compose up mongo`): {exc}"
        if os.environ.get("REQUIRE_DB"):
            pytest.fail(message)
        pytest.skip(message)
    yield client[os.environ["MONGODB_DB"]]
    client.drop_database(os.environ["MONGODB_DB"])
    client.close()


@pytest.fixture(scope="session")
def _app_client(_sync_db):
    # Entering the context runs the lifespan, which connects and creates indexes.
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def _clean_db(request):
    if request.node.get_closest_marker("no_db"):
        yield
        return
    db = request.getfixturevalue("_sync_db")
    for name in COLLECTIONS:
        db[name].delete_many({})
    yield


@pytest.fixture
def db(_sync_db):
    """Synchronous handle to the test database, for asserting on stored documents."""
    return _sync_db


@pytest.fixture
def client(_app_client):
    _app_client.cookies.clear()
    _app_client.headers.pop("Authorization", None)
    return _app_client


class User:
    """A registered user. `h` holds the Authorization header to pass to requests."""

    def __init__(self, data: dict, password: str):
        self.id = data["user"]["id"]
        self.email = data["user"]["email"]
        self.token = data["access_token"]
        self.password = password
        self.h = {"Authorization": f"Bearer {self.token}"}


@pytest.fixture
def register(client):
    def _register(email: str = "abdul@example.com", password: str = "password123", name: str = "Abdul") -> User:
        r = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
        assert r.status_code == 201, r.text
        client.cookies.clear()  # tests authenticate explicitly via the header
        return User(r.json(), password)

    return _register


@pytest.fixture
def user(register) -> User:
    return register()


@pytest.fixture
def add_tx(client):
    def _add(u: User, **overrides) -> dict:
        body = {
            "title": "Lunch",
            "amount": 250,
            "type": "expense",
            "category": "Food",
            "description": "",
            "date": "2026-11-24",
            **overrides,
        }
        r = client.post("/api/transactions", json=body, headers=u.h)
        assert r.status_code == 201, r.text
        return r.json()

    return _add
