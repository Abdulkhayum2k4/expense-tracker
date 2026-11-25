def test_register_returns_token_and_seeds_categories(client, db):
    r = client.post("/api/auth/register", json={"name": " Abdul ", "email": "Abdul@Example.com", "password": "password123"})
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"] and body["token_type"] == "bearer"
    assert body["user"]["name"] == "Abdul"
    assert body["user"]["email"] == "abdul@example.com"  # normalised

    stored = db.users.find_one({"email": "abdul@example.com"})
    assert stored["password_hash"].startswith("$argon2id$")
    assert db.categories.count_documents({"user_id": stored["_id"], "type": "expense"}) >= 5
    assert db.categories.count_documents({"user_id": stored["_id"], "type": "income"}) >= 3


def test_duplicate_email_is_rejected_case_insensitively(client, register):
    register(email="abdul@example.com")
    r = client.post("/api/auth/register", json={"name": "X", "email": "ABDUL@example.com", "password": "password123"})
    assert r.status_code == 409


def test_register_validates_input(client):
    r = client.post("/api/auth/register", json={"name": "A", "email": "a@b.com", "password": "short"})
    assert r.status_code == 422


def test_login(client, register):
    register(email="abdul@example.com", password="password123")
    ok = client.post("/api/auth/login", json={"email": "ABDUL@example.com", "password": "password123"})
    assert ok.status_code == 200
    assert ok.json()["user"]["email"] == "abdul@example.com"

    wrong = client.post("/api/auth/login", json={"email": "abdul@example.com", "password": "nope-nope"})
    unknown = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "password123"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # no hint about which part was wrong


def test_me_returns_user_without_password(client, user):
    r = client.get("/api/auth/me", headers=user.h)
    assert r.status_code == 200
    assert r.json()["email"] == user.email
    assert "password_hash" not in r.json()


def test_token_for_deleted_user_is_rejected(client, user, db):
    db.users.delete_many({})
    assert client.get("/api/auth/me", headers=user.h).status_code == 401
