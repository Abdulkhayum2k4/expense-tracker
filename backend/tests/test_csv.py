import csv
import io


def _export(client, user, **params):
    r = client.get("/api/transactions/export", params=params, headers=user.h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    text = r.content.decode("utf-8")
    assert text.startswith("﻿")  # BOM for Excel
    return list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))


# --- Export -------------------------------------------------------------------

def test_export_all_columns(client, user, add_tx):
    add_tx(user, title="Lunch", amount=250.5, category="Food", description="with, commas \"quoted\"", date="2026-11-24")
    add_tx(user, title="Salary", type="income", category="Salary", amount=60000, date="2026-11-01")
    rows = _export(client, user)
    assert rows == [
        {"date": "2026-11-24", "title": "Lunch", "type": "expense", "category": "Food",
         "amount": "250.5", "description": 'with, commas "quoted"'},
        {"date": "2026-11-01", "title": "Salary", "type": "income", "category": "Salary",
         "amount": "60000.0", "description": ""},
    ]


def test_export_uses_list_filters(client, user, add_tx):
    add_tx(user, title="Nov lunch", date="2026-11-24")
    add_tx(user, title="Oct lunch", date="2026-10-24")
    add_tx(user, title="Salary", type="income", category="Salary", amount=1, date="2026-11-01")
    assert [r["title"] for r in _export(client, user, type="expense")] == ["Nov lunch", "Oct lunch"]
    assert [r["title"] for r in _export(client, user, start_date="2026-11-01")] == ["Nov lunch", "Salary"]
    assert [r["title"] for r in _export(client, user, search="oct")] == ["Oct lunch"]


def test_export_is_per_user_and_needs_auth(client, register, add_tx):
    a = register(email="a@example.com")
    b = register(email="b@example.com")
    add_tx(a)
    assert _export(client, b) == []
    assert client.get("/api/transactions/export").status_code == 401


def test_export_neutralises_spreadsheet_formulas(client, user, add_tx):
    add_tx(user, title="=HYPERLINK(\"http://evil\")")
    assert _export(client, user)[0]["title"] == "'=HYPERLINK(\"http://evil\")"


# --- Import -------------------------------------------------------------------

def _row(**overrides):
    return {"title": "Coffee", "amount": 120, "type": "expense", "category": "Food", "date": "2026-11-05", **overrides}


def _import(client, user, rows, **extra):
    r = client.post("/api/transactions/import", json={"rows": rows, **extra}, headers=user.h)
    assert r.status_code == 200, r.text
    return r.json()


def test_import_mixed_file(client, user):
    result = _import(client, user, [
        _row(),
        _row(amount=-5),                                   # invalid amount
        _row(date="05/11/2026"),                           # not ISO
        _row(title="Gym", category="Fitness"),             # new category
        _row(title="Bonus", type="income", category="Salary", amount=5000),
    ])
    assert result["created"] == 3
    assert result["skipped_duplicates"] == 0
    assert result["created_categories"] == ["Fitness (expense)"]
    assert [e["row"] for e in result["errors"]] == [2, 3]
    assert "amount" in result["errors"][0]["message"] and "date" in result["errors"][1]["message"]

    listed = client.get("/api/transactions", headers=user.h).json()
    assert sorted(t["title"] for t in listed["items"]) == ["Bonus", "Coffee", "Gym"]


def test_import_can_refuse_new_categories(client, user):
    result = _import(client, user, [_row(), _row(category="Fitness")], create_missing_categories=False)
    assert result["created"] == 1 and result["created_categories"] == []
    assert result["errors"] == [{"row": 2, "message": "'Fitness' is not one of your expense categories"}]


def test_reimport_skips_duplicates_but_keeps_identical_rows_in_one_file(client, user):
    rows = [_row(), _row(), _row(title="Tea", amount=40)]  # two identical coffees on purpose
    first = _import(client, user, rows)
    assert (first["created"], first["skipped_duplicates"]) == (3, 0)

    again = _import(client, user, rows + [_row(title="New one")])
    assert (again["created"], again["skipped_duplicates"]) == (1, 3)
    assert client.get("/api/transactions", headers=user.h).json()["total"] == 4

    # Duplicate matching ignores case and surrounding spaces in the title.
    assert _import(client, user, [_row(title="  TEA ", amount=40)])["skipped_duplicates"] == 1


def test_import_limits(client, user):
    assert client.post("/api/transactions/import", json={"rows": []}, headers=user.h).status_code == 422
    too_many = {"rows": [_row()] * 5001}
    assert client.post("/api/transactions/import", json=too_many, headers=user.h).status_code == 422


def test_export_then_import_round_trip(client, register, add_tx):
    a = register(email="a@example.com")
    b = register(email="b@example.com")
    add_tx(a, title="Lunch", amount=250.5, description="team")
    add_tx(a, title="Salary", type="income", category="Salary", amount=60000, date="2026-11-01")

    rows = [{**r, "amount": float(r["amount"])} for r in _export(client, a)]
    result = _import(client, b, rows)
    assert result["created"] == 2 and result["errors"] == []
    assert _export(client, b) == _export(client, a)
