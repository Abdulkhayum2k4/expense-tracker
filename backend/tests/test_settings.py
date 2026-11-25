import pytest


def test_new_users_get_default_settings(client, user):
    me = client.get("/api/auth/me", headers=user.h).json()
    assert me["currency"] == "INR" and me["budget_alerts"] is True


def test_old_accounts_without_settings_get_defaults(client, user, db):
    db.users.update_one({}, {"$unset": {"currency": "", "budget_alerts": ""}})
    me = client.get("/api/auth/me", headers=user.h).json()
    assert me["currency"] == "INR" and me["budget_alerts"] is True


def test_patch_me_changes_only_sent_fields(client, user):
    r = client.patch("/api/auth/me", json={"currency": "USD"}, headers=user.h)
    assert r.status_code == 200
    assert r.json()["currency"] == "USD" and r.json()["name"] == "Abdul"

    r = client.patch("/api/auth/me", json={"name": "  Abdul K ", "budget_alerts": False}, headers=user.h)
    assert r.json() == {**r.json(), "name": "Abdul K", "budget_alerts": False, "currency": "USD"}
    assert client.get("/api/auth/me", headers=user.h).json()["name"] == "Abdul K"


@pytest.mark.parametrize("body", [{"currency": "XYZ"}, {"name": ""}, {"budget_alerts": "maybe"}])
def test_patch_me_validates(client, user, body):
    assert client.patch("/api/auth/me", json=body, headers=user.h).status_code == 422


# --- Budget alerts --------------------------------------------------------------

@pytest.fixture
def food_budget(client, user):
    r = client.post("/api/budgets", json={"category": "Food", "monthly_limit": 1000, "month": 11, "year": 2026}, headers=user.h)
    assert r.status_code == 201
    return r.json()


def _add(client, user, amount, **extra):
    body = {"title": "x", "amount": amount, "type": "expense", "category": "Food", "date": "2026-11-10", **extra}
    r = client.post("/api/transactions", json=body, headers=user.h)
    assert r.status_code == 201, r.text
    return r.json()


def test_alert_when_crossing_80_then_100_percent(client, user, food_budget):
    assert _add(client, user, 500)["budget_alert"] is None  # 50%

    alert = _add(client, user, 300)["budget_alert"]  # 80%
    assert alert == {"category": "Food", "level": "warning", "percent_used": 80.0, "spent": 800, "monthly_limit": 1000}

    assert _add(client, user, 100)["budget_alert"] is None  # 90%: still in the warning band

    alert = _add(client, user, 200)["budget_alert"]  # 110%
    assert alert["level"] == "exceeded" and alert["percent_used"] == 110.0

    assert _add(client, user, 50)["budget_alert"] is None  # already over


def test_jumping_straight_past_100_reports_exceeded(client, user, food_budget):
    assert _add(client, user, 1500)["budget_alert"]["level"] == "exceeded"


def test_no_alert_for_other_month_category_income_or_no_budget(client, user, food_budget):
    assert _add(client, user, 5000, date="2026-12-01")["budget_alert"] is None  # no December budget
    assert _add(client, user, 5000, category="Transport")["budget_alert"] is None  # no Transport budget
    assert _add(client, user, 5000, type="income", category="Salary")["budget_alert"] is None


def test_no_alert_when_disabled(client, user, food_budget):
    client.patch("/api/auth/me", json={"budget_alerts": False}, headers=user.h)
    assert _add(client, user, 5000)["budget_alert"] is None


def test_editing_a_transaction_can_trigger_an_alert(client, user, food_budget):
    tx = _add(client, user, 100)
    body = {"title": "x", "amount": 900, "type": "expense", "category": "Food", "date": "2026-11-10"}
    r = client.put(f"/api/transactions/{tx['id']}", json=body, headers=user.h)
    assert r.json()["budget_alert"]["level"] == "warning"  # 10% -> 90%

    # Editing it down and back up again within the same band doesn't re-alert.
    body["amount"] = 850
    assert client.put(f"/api/transactions/{tx['id']}", json=body, headers=user.h).json()["budget_alert"] is None
