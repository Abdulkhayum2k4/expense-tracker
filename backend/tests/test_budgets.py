NOV = {"month": 11, "year": 2026}


def _create(client, user, category="Food", limit=1000, **period):
    return client.post(
        "/api/budgets", json={"category": category, "monthly_limit": limit, **(period or NOV)}, headers=user.h
    )


def test_spent_counts_only_that_category_type_and_month(client, user, add_tx):
    add_tx(user, category="Food", amount=300, date="2026-11-01")
    add_tx(user, category="Food", amount=550, date="2026-11-30")
    add_tx(user, category="Food", amount=999, date="2026-10-31")  # previous month
    add_tx(user, category="Food", amount=999, date="2026-12-01")  # next month
    add_tx(user, category="Transport", amount=999, date="2026-11-10")  # other category
    client.post("/api/categories", json={"name": "Food", "type": "income"}, headers=user.h)
    add_tx(user, type="income", category="Food", amount=999, date="2026-11-10")  # income, same name

    r = _create(client, user, limit=1000)
    assert r.status_code == 201
    b = r.json()
    assert (b["spent"], b["remaining"], b["percent_used"]) == (850, 150, 85.0)

    listed = client.get("/api/budgets", params=NOV, headers=user.h).json()
    assert listed == [b]


def test_over_budget_has_negative_remaining(client, user, add_tx):
    add_tx(user, amount=1500)
    b = _create(client, user, limit=1000).json()
    assert b["remaining"] == -500 and b["percent_used"] == 150.0


def test_one_budget_per_category_per_month(client, user):
    assert _create(client, user).status_code == 201
    assert _create(client, user).status_code == 409
    assert _create(client, user, month=12, year=2026).status_code == 201


def test_only_expense_categories(client, user):
    assert _create(client, user, category="Salary").status_code == 422
    assert _create(client, user, category="Nope").status_code == 422


def test_update_and_delete(client, user, register):
    b = _create(client, user).json()
    r = client.put(f"/api/budgets/{b['id']}", json={"category": "Food", "monthly_limit": 2000, **NOV}, headers=user.h)
    assert r.status_code == 200 and r.json()["monthly_limit"] == 2000

    other = register(email="other@example.com")
    assert client.delete(f"/api/budgets/{b['id']}", headers=other.h).status_code == 404
    assert client.delete(f"/api/budgets/{b['id']}", headers=user.h).status_code == 204
    assert client.get("/api/budgets", params=NOV, headers=user.h).json() == []


def test_update_onto_existing_budget_conflicts(client, user):
    _create(client, user, category="Food")
    transport = _create(client, user, category="Transport").json()
    r = client.put(f"/api/budgets/{transport['id']}", json={"category": "Food", "monthly_limit": 5, **NOV}, headers=user.h)
    assert r.status_code == 409
