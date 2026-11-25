import pytest

from app.rate_limit import limiter


def _login(client, email="abdul@example.com", password="password123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_sets_httponly_cookie_that_authenticates(client, user):
    r = _login(client)
    cookie = r.headers["set-cookie"]
    assert "access_token=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/api" in cookie

    # No Authorization header: the cookie alone is enough.
    assert client.get("/api/auth/me").json()["email"] == user.email


def test_logout_clears_cookie(client, user):
    _login(client)
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_change_password(client, user):
    old_header = user.h
    r = client.put(
        "/api/auth/password",
        json={"current_password": user.password, "new_password": "brand-new-pass"},
        headers=user.h,
    )
    assert r.status_code == 200
    new_header = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Every token issued before the change is revoked; the new one works.
    assert client.get("/api/auth/me", headers=old_header).status_code == 401
    assert client.get("/api/auth/me", headers=new_header).status_code == 200
    assert _login(client, password=user.password).status_code == 401
    assert _login(client, password="brand-new-pass").status_code == 200


@pytest.mark.parametrize(
    "body, detail",
    [
        ({"current_password": "wrong-pass", "new_password": "brand-new-pass"}, "Current password is incorrect"),
        ({"current_password": "password123", "new_password": "password123"}, "must be different"),
    ],
)
def test_change_password_rejects(client, user, body, detail):
    r = client.put("/api/auth/password", json=body, headers=user.h)
    assert r.status_code == 400 and detail in r.json()["detail"]
    assert client.get("/api/auth/me", headers=user.h).status_code == 200  # still signed in


def test_delete_account_removes_all_user_data(client, register, add_tx, db):
    me = register(email="me@example.com")
    other = register(email="other@example.com")
    add_tx(me)
    add_tx(other)
    client.post("/api/budgets", json={"category": "Food", "monthly_limit": 1, "month": 11, "year": 2026}, headers=me.h)

    wrong = client.request("DELETE", "/api/auth/me", json={"password": "nope-nope"}, headers=me.h)
    assert wrong.status_code == 400

    r = client.request("DELETE", "/api/auth/me", json={"password": me.password}, headers=me.h)
    assert r.status_code == 204
    assert client.get("/api/auth/me", headers=me.h).status_code == 401

    survivor_id = db.users.find_one({"email": "other@example.com"})["_id"]
    for name in ("transactions", "categories", "budgets"):
        assert all(doc["user_id"] == survivor_id for doc in db[name].find()), name
    assert db.users.count_documents({}) == 1
    assert db.transactions.count_documents({}) == 1


@pytest.fixture
def rate_limited():
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


def test_login_is_rate_limited(client, user, rate_limited):
    codes = [_login(client, password="wrong-pass").status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]
