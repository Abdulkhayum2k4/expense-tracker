from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Query

from app.database import get_db
from app.deps import CurrentUser
from app.schemas import Breakdown, MonthComparison, MonthlySummary, YearTrend
from app.serializers import month_range, transaction_out

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

MonthParam = Annotated[int | None, Query(ge=1, le=12)]
YearParam = Annotated[int | None, Query(ge=2000, le=2100)]


def _resolve(month: int | None, year: int | None) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    return month or now.month, year or now.year


def _previous(month: int, year: int) -> tuple[int, int]:
    return (12, year - 1) if month == 1 else (month - 1, year)


async def _totals_by_category(user_id, start: datetime, end: datetime) -> dict[str, list[dict]]:
    """{'income': [{category, total}], 'expense': [...]} for start <= date < end, largest first."""
    pipeline = [
        {"$match": {"user_id": user_id, "date": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": {"type": "$type", "category": "$category"}, "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1, "_id.category": 1}},
    ]
    result: dict[str, list[dict]] = {"income": [], "expense": []}
    async for row in await get_db().transactions.aggregate(pipeline):
        result[row["_id"]["type"]].append({"category": row["_id"]["category"], "total": round(row["total"], 2)})
    return result


def _sum(rows: list[dict]) -> float:
    return round(sum(r["total"] for r in rows), 2)


@router.get("/summary", response_model=MonthlySummary)
async def monthly_summary(user: CurrentUser, month: MonthParam = None, year: YearParam = None):
    """Dashboard data for one month: totals, savings, running balance, breakdown, latest transactions."""
    month, year = _resolve(month, year)
    start, end = month_range(year, month)
    db = get_db()

    by_category = await _totals_by_category(user["_id"], start, end)
    income = _sum(by_category["income"])
    expense = _sum(by_category["expense"])
    savings = round(income - expense, 2)

    # Running balance: everything up to the end of the selected month.
    balance_pipeline = [
        {"$match": {"user_id": user["_id"], "date": {"$lt": end}}},
        {"$group": {"_id": "$type", "total": {"$sum": "$amount"}}},
    ]
    lifetime = {row["_id"]: row["total"] async for row in await db.transactions.aggregate(balance_pipeline)}
    total_balance = round(lifetime.get("income", 0.0) - lifetime.get("expense", 0.0), 2)

    recent_cursor = (
        db.transactions.find({"user_id": user["_id"], "date": {"$gte": start, "$lt": end}})
        .sort([("date", -1), ("_id", -1)])
        .limit(5)
    )
    recent = [transaction_out(doc) async for doc in recent_cursor]

    return {
        "month": month,
        "year": year,
        "income": income,
        "expense": expense,
        "savings": savings,
        "savings_rate": round(savings / income * 100, 1) if income else None,
        "total_balance": total_balance,
        "expense_by_category": by_category["expense"],
        "income_by_category": by_category["income"],
        "recent_transactions": recent,
    }


@router.get("/trend", response_model=YearTrend)
async def yearly_trend(user: CurrentUser, year: YearParam = None):
    """Income and expense for each month of a year."""
    year = year or datetime.now(timezone.utc).year
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    pipeline = [
        {"$match": {"user_id": user["_id"], "date": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": {"month": {"$month": "$date"}, "type": "$type"}, "total": {"$sum": "$amount"}}},
    ]
    points = {m: {"month": m, "income": 0.0, "expense": 0.0} for m in range(1, 13)}
    async for row in await get_db().transactions.aggregate(pipeline):
        points[row["_id"]["month"]][row["_id"]["type"]] = round(row["total"], 2)
    return {"year": year, "points": list(points.values())}


@router.get("/breakdown", response_model=Breakdown)
async def breakdown(user: CurrentUser, year: YearParam = None, month: MonthParam = None):
    """Category totals for one month, or for the whole year when month is omitted."""
    year = year or datetime.now(timezone.utc).year
    if month:
        start, end = month_range(year, month)
    else:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    by_category = await _totals_by_category(user["_id"], start, end)
    return {
        "year": year,
        "month": month,
        "income": _sum(by_category["income"]),
        "expense": _sum(by_category["expense"]),
        "expense_by_category": by_category["expense"],
        "income_by_category": by_category["income"],
    }


@router.get("/compare", response_model=MonthComparison)
async def compare_with_previous_month(user: CurrentUser, month: MonthParam = None, year: YearParam = None):
    """Spending per category in a month next to the month before it."""
    month, year = _resolve(month, year)
    prev_month, prev_year = _previous(month, year)
    current = await _totals_by_category(user["_id"], *month_range(year, month))
    previous = await _totals_by_category(user["_id"], *month_range(prev_year, prev_month))

    cur = {r["category"]: r["total"] for r in current["expense"]}
    prev = {r["category"]: r["total"] for r in previous["expense"]}
    rows = []
    for category in cur.keys() | prev.keys():
        c, p = cur.get(category, 0.0), prev.get(category, 0.0)
        rows.append({
            "category": category,
            "current": c,
            "previous": p,
            "change": round(c - p, 2),
            "change_pct": round((c - p) / p * 100, 1) if p else None,
        })
    rows.sort(key=lambda r: (-max(r["current"], r["previous"]), r["category"]))

    return {
        "month": month,
        "year": year,
        "previous_month": prev_month,
        "previous_year": prev_year,
        "current_total": _sum(current["expense"]),
        "previous_total": _sum(previous["expense"]),
        "categories": rows,
    }
