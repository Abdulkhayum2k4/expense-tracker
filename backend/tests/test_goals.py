from datetime import date, datetime, timezone

import pytest

from app.routers import goals as goals_router

TODAY = date(2026, 11, 25)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(goals_router, "_today", lambda: TODAY)


def _create(client, user, **body):
    r = client.post("/api/goals", json={"name": "Laptop", "target_amount": 80000, **body}, headers=user.h)
    assert r.status_code == 201, r.text
    return r.json()


def _contribute(client, user, goal_id, amount, on="2026-11-25", note=""):
    return client.post(
        f"/api/goals/{goal_id}/contributions", json={"amount": amount, "date": on, "note": note}, headers=user.h
    )


def _set_created(db, goal_id, day: date):
    from bson import ObjectId

    db.goals.update_one({"_id": ObjectId(goal_id)}, {"$set": {"created_at": datetime(day.year, day.month, day.day, tzinfo=timezone.utc)}})


def test_create_without_deadline(client, user):
    g = _create(client, user)
    assert g["saved"] == 0 and g["remaining"] == 80000 and g["percent"] == 0
    assert g["status"] == "no_deadline" and g["months_left"] is None and g["monthly_needed"] is None
    assert g["contributions"] == []


def test_contributions_progress_and_completion(client, user):
    g = _create(client, user, target_amount=1000)
    g = _contribute(client, user, g["id"], 300, note="first").json()
    g = _contribute(client, user, g["id"], 450.555, on="2026-11-26").json()
    assert g["saved"] == 750.56 and g["remaining"] == 249.44 and g["percent"] == 75.1
    assert [c["amount"] for c in g["contributions"]] == [450.56, 300]  # newest first

    g = _contribute(client, user, g["id"], -100).json()  # withdrawal
    assert g["saved"] == 650.56

    g = _contribute(client, user, g["id"], 500).json()
    assert g["status"] == "completed" and g["remaining"] == 0 and g["percent"] == 115.1


def test_cannot_withdraw_more_than_saved_or_add_zero(client, user):
    g = _create(client, user)
    _contribute(client, user, g["id"], 100)
    r = _contribute(client, user, g["id"], -150)
    assert r.status_code == 422 and "100.00" in r.json()["detail"]
    assert _contribute(client, user, g["id"], 0).status_code == 422


def test_removing_a_contribution(client, user):
    g = _create(client, user)
    deposit = _contribute(client, user, g["id"], 500).json()["contributions"][0]
    g = _contribute(client, user, g["id"], -400).json()
    # Removing the deposit would leave -400 saved.
    assert client.delete(f"/api/goals/{g['id']}/contributions/{deposit['id']}", headers=user.h).status_code == 422

    withdrawal = next(c for c in g["contributions"] if c["amount"] == -400)
    r = client.delete(f"/api/goals/{g['id']}/contributions/{withdrawal['id']}", headers=user.h)
    assert r.status_code == 200 and r.json()["saved"] == 500
    assert client.delete(f"/api/goals/{g['id']}/contributions/{withdrawal['id']}", headers=user.h).status_code == 404


def test_monthly_needed_and_months_left(client, user):
    # Today is 25 Nov 2026; a 31 May 2027 deadline leaves Nov..May = 7 months.
    g = _create(client, user, target_amount=70000, target_date="2027-05-31")
    assert g["months_left"] == 7 and g["monthly_needed"] == 10000

    # A deadline later this month still leaves this month.
    g = _create(client, user, target_amount=500, target_date="2026-11-30")
    assert g["months_left"] == 1 and g["monthly_needed"] == 500


@pytest.mark.parametrize(
    "saved, expected_status",
    [(5000, "on_track"), (4999, "behind")],
)
def test_on_track_means_keeping_an_even_pace(client, user, db, saved, expected_status):
    # Created 50 days ago, due in 50 days: half-way through, so 50% of 10,000 is the pace.
    g = _create(client, user, target_amount=10000, target_date="2027-01-14")
    _set_created(db, g["id"], date(2026, 10, 6))
    _contribute(client, user, g["id"], saved)
    got = client.get("/api/goals", headers=user.h).json()[0]
    assert got["status"] == expected_status


def test_overdue_goal_is_behind_and_needs_the_rest_now(client, user, db):
    g = _create(client, user, target_amount=1000, target_date="2026-11-01")
    _set_created(db, g["id"], date(2026, 9, 1))
    got = client.get("/api/goals", headers=user.h).json()[0]
    assert got["status"] == "behind" and got["months_left"] == 0 and got["monthly_needed"] == 1000


def test_update_list_order_and_delete(client, user):
    later = _create(client, user, name="Car", target_date="2028-01-01")
    sooner = _create(client, user, name="Trip", target_date="2027-03-01")
    done = _create(client, user, name="Phone", target_amount=100)
    _contribute(client, user, done["id"], 100)
    open_ended = _create(client, user, name="Rainy day")

    names = [g["name"] for g in client.get("/api/goals", headers=user.h).json()]
    assert names == ["Trip", "Car", "Rainy day", "Phone"]  # by deadline, completed last

    r = client.put(f"/api/goals/{later['id']}", json={"name": "New car", "target_amount": 500000, "target_date": None}, headers=user.h)
    assert r.status_code == 200 and r.json()["name"] == "New car" and r.json()["target_date"] is None

    assert client.delete(f"/api/goals/{sooner['id']}", headers=user.h).status_code == 204
    assert len(client.get("/api/goals", headers=user.h).json()) == 3
    assert open_ended["status"] == "no_deadline"


def test_validation(client, user):
    bad = [{"name": "", "target_amount": 10}, {"name": "X", "target_amount": 0}, {"name": "X", "target_amount": -5}]
    for body in bad:
        assert client.post("/api/goals", json=body, headers=user.h).status_code == 422


def test_goals_are_private(client, register):
    a = register(email="a@example.com")
    b = register(email="b@example.com")
    g = _create(client, a)
    assert client.get("/api/goals", headers=b.h).json() == []
    assert client.put(f"/api/goals/{g['id']}", json={"name": "X", "target_amount": 1}, headers=b.h).status_code == 404
    assert client.delete(f"/api/goals/{g['id']}", headers=b.h).status_code == 404
    assert _contribute(client, b, g["id"], 10).status_code == 404


def test_deleting_the_account_deletes_goals(client, user, db):
    _create(client, user)
    client.request("DELETE", "/api/auth/me", json={"password": user.password}, headers=user.h)
    assert db.goals.count_documents({}) == 0
