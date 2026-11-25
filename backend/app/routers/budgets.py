from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from pymongo.errors import DuplicateKeyError

from app.database import get_db
from app.deps import CurrentUser, parse_object_id
from app.schemas import BudgetIn, BudgetOut
from app.serializers import month_range

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


async def _spent_by_category(user_id, year: int, month: int) -> dict[str, float]:
    start, end = month_range(year, month)
    pipeline = [
        {"$match": {"user_id": user_id, "type": "expense", "date": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
    ]
    cursor = await get_db().transactions.aggregate(pipeline)
    return {row["_id"]: row["total"] async for row in cursor}


def _budget_out(doc: dict, spent: float) -> dict:
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


async def _ensure_expense_category(user_id, name: str) -> None:
    found = await get_db().categories.find_one({"user_id": user_id, "name": name, "type": "expense"})
    if found is None:
        raise HTTPException(422, f"'{name}' is not one of your expense categories")


async def _with_spent(user_id, doc: dict) -> dict:
    spent = await _spent_by_category(user_id, doc["year"], doc["month"])
    return _budget_out(doc, spent.get(doc["category"], 0.0))


@router.get("", response_model=list[BudgetOut])
async def list_budgets(
    user: CurrentUser,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
):
    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year
    cursor = get_db().budgets.find({"user_id": user["_id"], "month": month, "year": year}).sort("category", 1)
    budgets = [doc async for doc in cursor]
    spent = await _spent_by_category(user["_id"], year, month)
    return [_budget_out(doc, spent.get(doc["category"], 0.0)) for doc in budgets]


@router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
async def create_budget(data: BudgetIn, user: CurrentUser):
    await _ensure_expense_category(user["_id"], data.category)
    doc = {"user_id": user["_id"], **data.model_dump()}
    try:
        result = await get_db().budgets.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A budget for {data.category} in {data.month}/{data.year} already exists"
        )
    doc["_id"] = result.inserted_id
    return await _with_spent(user["_id"], doc)


@router.put("/{budget_id}", response_model=BudgetOut)
async def update_budget(budget_id: str, data: BudgetIn, user: CurrentUser):
    oid = parse_object_id(budget_id, "Budget")
    await _ensure_expense_category(user["_id"], data.category)
    try:
        doc = await get_db().budgets.find_one_and_update(
            {"_id": oid, "user_id": user["_id"]},
            {"$set": data.model_dump()},
            return_document=True,
        )
    except DuplicateKeyError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A budget for {data.category} in {data.month}/{data.year} already exists"
        )
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget not found")
    return await _with_spent(user["_id"], doc)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(budget_id: str, user: CurrentUser):
    oid = parse_object_id(budget_id, "Budget")
    result = await get_db().budgets.delete_one({"_id": oid, "user_id": user["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
