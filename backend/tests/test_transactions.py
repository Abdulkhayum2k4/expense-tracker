def test_crud(client, user, add_tx):
    tx = add_tx(user, title="Lunch", amount=250.5, description="with friends")
    assert tx.pop("budget_alert") is None
    assert tx["date"] == "2026-11-24" and tx["amount"] == 250.5

    got = client.get(f"/api/transactions/{tx['id']}", headers=user.h)
    assert got.status_code == 200 and got.json() == tx

    update = {**tx, "title": "Team lunch", "amount": 400}
    update.pop("id")
    r = client.put(f"/api/transactions/{tx['id']}", json=update, headers=user.h)
    assert r.status_code == 200 and r.json()["title"] == "Team lunch" and r.json()["amount"] == 400

    assert client.delete(f"/api/transactions/{tx['id']}", headers=user.h).status_code == 204
    assert client.get(f"/api/transactions/{tx['id']}", headers=user.h).status_code == 404
    assert client.delete(f"/api/transactions/{tx['id']}", headers=user.h).status_code == 404


def test_category_must_exist_for_that_type(client, user):
    base = {"title": "x", "amount": 1, "date": "2026-11-24"}
    unknown = client.post("/api/transactions", json={**base, "type": "expense", "category": "Nope"}, headers=user.h)
    wrong_type = client.post("/api/transactions", json={**base, "type": "expense", "category": "Salary"}, headers=user.h)
    assert unknown.status_code == wrong_type.status_code == 422


def test_filters(client, user, add_tx):
    add_tx(user, title="Lunch", category="Food", date="2026-11-24")
    add_tx(user, title="Bus pass", category="Transport", date="2026-11-02", description="monthly")
    add_tx(user, title="October dinner", category="Food", date="2026-10-15")
    add_tx(user, title="Salary", type="income", category="Salary", amount=60000, date="2026-11-01")

    def titles(**params):
        r = client.get("/api/transactions", params=params, headers=user.h)
        assert r.status_code == 200
        return [t["title"] for t in r.json()["items"]]

    assert titles() == ["Lunch", "Bus pass", "Salary", "October dinner"]  # newest first
    assert titles(type="income") == ["Salary"]
    assert titles(category="Food") == ["Lunch", "October dinner"]
    assert titles(start_date="2026-11-01", end_date="2026-11-24") == ["Lunch", "Bus pass", "Salary"]
    assert titles(end_date="2026-11-01") == ["Salary", "October dinner"]  # end date is inclusive
    assert titles(search="MONTHLY") == ["Bus pass"]  # description, case-insensitive
    assert titles(search="dinner") == ["October dinner"]
    assert titles(search=".*") == []  # treated as text, not a regex


def test_paging(client, user, add_tx):
    for day in range(1, 8):
        add_tx(user, title=f"T{day}", date=f"2026-11-{day:02d}")
    r = client.get("/api/transactions", params={"page": 2, "page_size": 3}, headers=user.h).json()
    assert r["total"] == 7 and r["page"] == 2 and r["page_size"] == 3
    assert [t["title"] for t in r["items"]] == ["T4", "T3", "T2"]
    assert client.get("/api/transactions", params={"page_size": 101}, headers=user.h).status_code == 422


def test_users_cannot_see_or_touch_each_others_transactions(client, register, add_tx):
    a = register(email="a@example.com")
    b = register(email="b@example.com")
    tx = add_tx(a)

    assert client.get("/api/transactions", headers=b.h).json()["total"] == 0
    assert client.get(f"/api/transactions/{tx['id']}", headers=b.h).status_code == 404
    body = {"title": "hacked", "amount": 1, "type": "expense", "category": "Food", "date": "2026-11-24"}
    assert client.put(f"/api/transactions/{tx['id']}", json=body, headers=b.h).status_code == 404
    assert client.delete(f"/api/transactions/{tx['id']}", headers=b.h).status_code == 404
    assert client.get(f"/api/transactions/{tx['id']}", headers=a.h).json()["title"] == "Lunch"


def test_malformed_id_is_404(client, user):
    assert client.get("/api/transactions/123", headers=user.h).status_code == 404
