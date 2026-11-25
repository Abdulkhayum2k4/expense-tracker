import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.budget_utils import BudgetWatch
from app.database import get_db
from app.deps import CurrentUser, parse_object_id
from app.schemas import TransactionIn, TransactionOut, TransactionPage, TransactionSaved, TxType
from app.serializers import to_utc_datetime, transaction_out

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


async def _ensure_category_exists(user_id, name: str, tx_type: str) -> None:
    found = await get_db().categories.find_one({"user_id": user_id, "name": name, "type": tx_type})
    if found is None:
        raise HTTPException(
            422, f"'{name}' is not one of your {tx_type} categories"
        )


def _to_doc(data: TransactionIn) -> dict:
    doc = data.model_dump()
    doc["date"] = to_utc_datetime(data.date)
    return doc


@router.get("", response_model=TransactionPage)
async def list_transactions(
    user: CurrentUser,
    type: TxType | None = None,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    query: dict = {"user_id": user["_id"]}
    if type:
        query["type"] = type
    if category:
        query["category"] = category
    if start_date or end_date:
        query["date"] = {}
        if start_date:
            query["date"]["$gte"] = to_utc_datetime(start_date)
        if end_date:
            query["date"]["$lte"] = to_utc_datetime(end_date)
    if search:
        pattern = re.escape(search.strip())
        query["$or"] = [
            {"title": {"$regex": pattern, "$options": "i"}},
            {"description": {"$regex": pattern, "$options": "i"}},
        ]

    db = get_db()
    total = await db.transactions.count_documents(query)
    cursor = (
        db.transactions.find(query)
        .sort([("date", -1), ("_id", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [transaction_out(doc) async for doc in cursor]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _budget_watch(user: dict, data: TransactionIn) -> BudgetWatch:
    return BudgetWatch(user, data.type, data.category, data.date.year, data.date.month)


@router.post("", response_model=TransactionSaved, status_code=status.HTTP_201_CREATED)
async def create_transaction(data: TransactionIn, user: CurrentUser):
    await _ensure_category_exists(user["_id"], data.category, data.type)
    watch = _budget_watch(user, data)
    await watch.before()
    doc = {"user_id": user["_id"], **_to_doc(data)}
    result = await get_db().transactions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return {**transaction_out(doc), "budget_alert": await watch.after()}


@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(transaction_id: str, user: CurrentUser):
    oid = parse_object_id(transaction_id, "Transaction")
    doc = await get_db().transactions.find_one({"_id": oid, "user_id": user["_id"]})
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return transaction_out(doc)


@router.put("/{transaction_id}", response_model=TransactionSaved)
async def update_transaction(transaction_id: str, data: TransactionIn, user: CurrentUser):
    oid = parse_object_id(transaction_id, "Transaction")
    await _ensure_category_exists(user["_id"], data.category, data.type)
    watch = _budget_watch(user, data)
    await watch.before()
    doc = await get_db().transactions.find_one_and_update(
        {"_id": oid, "user_id": user["_id"]},
        {"$set": _to_doc(data)},
        return_document=True,
    )
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return {**transaction_out(doc), "budget_alert": await watch.after()}


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(transaction_id: str, user: CurrentUser):
    oid = parse_object_id(transaction_id, "Transaction")
    result = await get_db().transactions.delete_one({"_id": oid, "user_id": user["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
