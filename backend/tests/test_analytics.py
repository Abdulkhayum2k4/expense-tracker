import pytest


@pytest.fixture
def history(user, add_tx):
    """Oct: +50,000 / -20,000.  Nov: +60,000 / -(300 + 200 + 1,500)."""
    add_tx(user, title="Oct salary", type="income", category="Salary", amount=50000, date="2026-10-01")
    add_tx(user, title="Oct rent", category="Rent", amount=20000, date="2026-10-05")
    add_tx(user, title="Nov salary", type="income", category="Salary", amount=60000, date="2026-11-01")
    add_tx(user, title="Lunch", category="Food", amount=300, date="2026-11-03")
    add_tx(user, title="Dinner", category="Food", amount=200, date="2026-11-20")
    add_tx(user, title="Shoes", category="Shopping", amount=1500, date="2026-11-21")
    add_tx(user, title="Dec gift", category="Shopping", amount=999, date="2026-12-02")
    return user


def test_summary(client, history):
    s = client.get("/api/analytics/summary", params={"month": 11, "year": 2026}, headers=history.h).json()
    assert (s["income"], s["expense"], s["savings"]) == (60000, 2000, 58000)
    assert s["savings_rate"] == pytest.approx(96.7)
    # Everything up to the end of November: (50,000 - 20,000) + 58,000. December is excluded.
    assert s["total_balance"] == 88000
    assert s["expense_by_category"] == [
        {"category": "Shopping", "total": 1500},
        {"category": "Food", "total": 500},
    ]
    assert s["income_by_category"] == [{"category": "Salary", "total": 60000}]
    assert [t["title"] for t in s["recent_transactions"]] == ["Shoes", "Dinner", "Lunch", "Nov salary"]


def test_summary_without_income(client, user, add_tx):
    add_tx(user, amount=100, date="2026-11-03")
    s = client.get("/api/analytics/summary", params={"month": 11, "year": 2026}, headers=user.h).json()
    assert s["savings"] == -100 and s["savings_rate"] is None and s["total_balance"] == -100


def test_trend(client, history):
    t = client.get("/api/analytics/trend", params={"year": 2026}, headers=history.h).json()
    assert [p["month"] for p in t["points"]] == list(range(1, 13))
    by_month = {p["month"]: p for p in t["points"]}
    assert by_month[10] == {"month": 10, "income": 50000, "expense": 20000}
    assert by_month[11] == {"month": 11, "income": 60000, "expense": 2000}
    assert by_month[1] == {"month": 1, "income": 0, "expense": 0}


def test_breakdown_month_and_year(client, history):
    month = client.get("/api/analytics/breakdown", params={"year": 2026, "month": 11}, headers=history.h).json()
    assert month["month"] == 11 and month["expense"] == 2000

    year = client.get("/api/analytics/breakdown", params={"year": 2026}, headers=history.h).json()
    assert year["month"] is None
    assert year["expense"] == 20000 + 2000 + 999
    assert year["expense_by_category"][0] == {"category": "Rent", "total": 20000}
    assert {"category": "Shopping", "total": 2499} in year["expense_by_category"]


def test_compare_across_year_boundary(client, user, add_tx):
    add_tx(user, category="Food", amount=400, date="2025-12-10")
    add_tx(user, category="Rent", amount=1000, date="2025-12-01")
    add_tx(user, category="Food", amount=500, date="2026-01-10")
    add_tx(user, category="Health", amount=50, date="2026-01-11")

    c = client.get("/api/analytics/compare", params={"month": 1, "year": 2026}, headers=user.h).json()
    assert (c["previous_month"], c["previous_year"]) == (12, 2025)
    assert (c["current_total"], c["previous_total"]) == (550, 1400)
    rows = {r["category"]: r for r in c["categories"]}
    assert rows["Food"] == {"category": "Food", "current": 500, "previous": 400, "change": 100, "change_pct": 25.0}
    assert rows["Rent"]["change"] == -1000 and rows["Rent"]["change_pct"] == -100.0
    assert rows["Health"]["change_pct"] is None  # new this month
    assert [r["category"] for r in c["categories"]] == ["Rent", "Food", "Health"]


def test_analytics_are_per_user(client, history, register):
    other = register(email="other@example.com")
    s = client.get("/api/analytics/summary", params={"month": 11, "year": 2026}, headers=other.h).json()
    assert s["income"] == s["expense"] == s["total_balance"] == 0
