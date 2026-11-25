"""Budget maths shared by the budgets and transactions routers."""
from app.database import get_db
from app.serializers import month_range

WARNING_PERCENT = 80


async def spent_by_category(user_id, year: int, month: int, category: str | None = None) -> dict[str, float]:
    """Expense totals per category for one month (optionally just one category)."""
    start, end = month_range(year, month)
    match: dict = {"user_id": user_id, "type": "expense", "date": {"$gte": start, "$lt": end}}
    if category is not None:
        match["category"] = category
    pipeline = [{"$match": match}, {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}}]
    return {row["_id"]: row["total"] async for row in await get_db().transactions.aggregate(pipeline)}


def budget_out(doc: dict, spent: float) -> dict:
    limit = doc["monthly_limit"]
    return {
        "id": str(doc["_id"]),
        "category": doc["category"],
        "monthly_limit": limit,
        "month": doc["month"],
        "year": doc["year"],
        "spent": round(spent, 2),
        "remaining": round(limit - spent, 2),
        "percent_used": round(spent / limit * 100, 1) if limit else 0.0,
    }


def _level(percent: float) -> int:
    """0 = under 80%, 1 = 80-100%, 2 = over budget."""
    if percent > 100:
        return 2
    return 1 if percent >= WARNING_PERCENT else 0


class BudgetWatch:
    """Detects when a transaction change pushes a budget across 80% or past 100%.

    Call `await watch.before()` before writing the transaction and `await watch.after()`
    after it; `after()` returns an alert dict, or None when nothing new was crossed.
    """

    def __init__(self, user: dict, tx_type: str, category: str, year: int, month: int):
        self.user = user
        self.active = tx_type == "expense" and user.get("budget_alerts", True)
        self.category, self.year, self.month = category, year, month
        self.budget: dict | None = None
        self.spent_before = 0.0

    async def _spent(self) -> float:
        totals = await spent_by_category(self.user["_id"], self.year, self.month, self.category)
        return totals.get(self.category, 0.0)

    async def before(self) -> None:
        if not self.active:
            return
        self.budget = await get_db().budgets.find_one(
            {"user_id": self.user["_id"], "category": self.category, "year": self.year, "month": self.month}
        )
        if self.budget:
            self.spent_before = await self._spent()

    async def after(self) -> dict | None:
        if not self.budget:
            return None
        spent = await self._spent()
        status = budget_out(self.budget, spent)
        before_pct = self.spent_before / self.budget["monthly_limit"] * 100
        new_level = _level(status["percent_used"])
        if new_level <= _level(before_pct):
            return None
        return {
            "category": self.category,
            "level": "exceeded" if new_level == 2 else "warning",
            "percent_used": status["percent_used"],
            "spent": status["spent"],
            "monthly_limit": status["monthly_limit"],
        }
