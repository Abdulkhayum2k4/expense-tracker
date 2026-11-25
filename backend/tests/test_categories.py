def _category(client, user, name, type_="expense"):
    cats = client.get("/api/categories", params={"type": type_}, headers=user.h).json()
    return next(c for c in cats if c["name"] == name)


def test_list_filters_by_type(client, user):
    expense = client.get("/api/categories", params={"type": "expense"}, headers=user.h).json()
    assert expense and all(c["type"] == "expense" for c in expense)
    everything = client.get("/api/categories", headers=user.h).json()
    assert len(everything) > len(expense)


def test_create_and_duplicates(client, user):
    r = client.post("/api/categories", json={"name": " Groceries ", "type": "expense"}, headers=user.h)
    assert r.status_code == 201 and r.json()["name"] == "Groceries"

    dup = client.post("/api/categories", json={"name": "Groceries", "type": "expense"}, headers=user.h)
    assert dup.status_code == 409
    # Same name with the other type is a different category.
    other_type = client.post("/api/categories", json={"name": "Groceries", "type": "income"}, headers=user.h)
    assert other_type.status_code == 201


def test_rename_carries_over_to_transactions_and_budgets(client, user, add_tx):
    tx = add_tx(user, category="Food")
    client.post("/api/budgets", json={"category": "Food", "monthly_limit": 5000, "month": 11, "year": 2026}, headers=user.h)
    food = _category(client, user, "Food")

    r = client.put(f"/api/categories/{food['id']}", json={"name": "Eating out", "type": "expense"}, headers=user.h)
    assert r.status_code == 200

    assert client.get(f"/api/transactions/{tx['id']}", headers=user.h).json()["category"] == "Eating out"
    budgets = client.get("/api/budgets", params={"month": 11, "year": 2026}, headers=user.h).json()
    assert [b["category"] for b in budgets] == ["Eating out"]
    assert budgets[0]["spent"] == 250


def test_rename_onto_existing_name_conflicts(client, user):
    food = _category(client, user, "Food")
    r = client.put(f"/api/categories/{food['id']}", json={"name": "Transport", "type": "expense"}, headers=user.h)
    assert r.status_code == 409


def test_cannot_change_type_while_in_use(client, user, add_tx):
    add_tx(user, category="Food")
    food = _category(client, user, "Food")
    r = client.put(f"/api/categories/{food['id']}", json={"name": "Food", "type": "income"}, headers=user.h)
    assert r.status_code == 409


def test_delete(client, user, add_tx):
    add_tx(user, category="Food")
    food = _category(client, user, "Food")
    assert client.delete(f"/api/categories/{food['id']}", headers=user.h).status_code == 409

    client.post("/api/budgets", json={"category": "Health", "monthly_limit": 100, "month": 11, "year": 2026}, headers=user.h)
    health = _category(client, user, "Health")
    assert client.delete(f"/api/categories/{health['id']}", headers=user.h).status_code == 204
    # Its budget goes with it.
    assert client.get("/api/budgets", params={"month": 11, "year": 2026}, headers=user.h).json() == []


def test_other_users_category_is_not_found(client, register):
    a = register(email="a@example.com")
    b = register(email="b@example.com")
    food_a = _category(client, a, "Food")
    assert client.put(f"/api/categories/{food_a['id']}", json={"name": "Mine", "type": "expense"}, headers=b.h).status_code == 404
    assert client.delete(f"/api/categories/{food_a['id']}", headers=b.h).status_code == 404
    assert client.delete("/api/categories/not-an-id", headers=b.h).status_code == 404
