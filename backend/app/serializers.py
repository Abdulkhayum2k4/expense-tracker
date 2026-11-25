"""Convert MongoDB documents to API response dicts, and dates to stored datetimes."""
from datetime import date, datetime, timezone


def to_utc_datetime(d: date) -> datetime:
    """Transactions store a calendar date as midnight UTC."""
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def month_range(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=timezone.utc)
    return start, end


def user_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "email": doc["email"],
        "created_at": doc["created_at"],
        # Defaults cover accounts created before these settings existed.
        "currency": doc.get("currency", "INR"),
        "budget_alerts": doc.get("budget_alerts", True),
    }


def category_out(doc: dict) -> dict:
    return {"id": str(doc["_id"]), "name": doc["name"], "type": doc["type"]}


def transaction_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc["title"],
        "amount": doc["amount"],
        "type": doc["type"],
        "category": doc["category"],
        "description": doc.get("description", ""),
        "date": doc["date"].date(),
    }
