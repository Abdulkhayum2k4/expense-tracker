import csv
import io
import re
from collections import Counter
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.budget_utils import BudgetWatch
from app.database import get_db
from app.deps import CurrentUser, parse_object_id
from app.schemas import (
    ImportRequest,
    ImportResult,
    TransactionIn,
    TransactionOut,
    TransactionPage,
    TransactionSaved,
    TxType,
)
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


def _filter_query(
    type: TxType | None = None,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> dict:
    """Mongo filter from the list/export query parameters (without the user_id scope)."""
    query: dict = {}
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
    return query


Filters = Annotated[dict, Depends(_filter_query)]


@router.get("", response_model=TransactionPage)
async def list_transactions(
    user: CurrentUser,
    filters: Filters,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    query = {**filters, "user_id": user["_id"]}
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


EXPORT_COLUMNS = ["date", "title", "type", "category", "amount", "description"]


@router.get("/export", response_class=StreamingResponse)
async def export_transactions(user: CurrentUser, filters: Filters):
    """All matching transactions as CSV (same filters as the list, no paging)."""
    cursor = get_db().transactions.find({**filters, "user_id": user["_id"]}).sort([("date", -1), ("_id", -1)])

    async def rows():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        # A byte-order mark makes Excel read the file as UTF-8 (so ₹ and non-English text survive).
        buffer.write("﻿")
        writer.writerow(EXPORT_COLUMNS)
        async for doc in cursor:
            tx = transaction_out(doc)
            writer.writerow([tx["date"].isoformat(), *(_csv_safe(tx[c]) for c in EXPORT_COLUMNS[1:])])
            if buffer.tell() > 64_000:
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate()
        yield buffer.getvalue()

    filename = f"transactions-{date.today().isoformat()}.csv"
    return StreamingResponse(
        rows(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _csv_safe(value):
    """Stop spreadsheet apps from running a cell as a formula (CSV injection)."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


@router.post("/import", response_model=ImportResult)
async def import_transactions(data: ImportRequest, user: CurrentUser):
    """Validate rows one by one, create what is valid, and report the rest.

    Rows that match an existing transaction (same date, title, amount and type) are
    skipped, so importing the same file twice doesn't create duplicates.
    """
    db = get_db()
    errors: list[dict] = []
    valid: list[tuple[int, TransactionIn]] = []
    for i, raw in enumerate(data.rows, start=1):
        try:
            valid.append((i, TransactionIn.model_validate(raw)))
        except ValidationError as exc:
            first = exc.errors()[0]
            field = ".".join(str(p) for p in first["loc"])
            errors.append({"row": i, "message": f"{field}: {first['msg']}" if field else first["msg"]})

    # Categories: create missing ones, or reject their rows.
    existing = {
        (c["type"], c["name"])
        async for c in db.categories.find({"user_id": user["_id"]}, {"type": 1, "name": 1})
    }
    missing = {(tx.type, tx.category) for _, tx in valid} - existing
    created_categories: list[str] = []
    if missing and data.create_missing_categories:
        await db.categories.insert_many(
            [{"user_id": user["_id"], "type": t, "name": n} for t, n in sorted(missing)]
        )
        created_categories = [f"{n} ({t})" for t, n in sorted(missing)]
    elif missing:
        kept = []
        for i, tx in valid:
            if (tx.type, tx.category) in missing:
                errors.append({"row": i, "message": f"'{tx.category}' is not one of your {tx.type} categories"})
            else:
                kept.append((i, tx))
        valid = kept

    # Duplicates: compare against what's already stored in the same date range,
    # counting matches so two genuinely identical rows in one file both import.
    skipped = 0
    to_insert: list[dict] = []
    if valid:
        dates = [tx.date for _, tx in valid]
        stored = Counter()
        async for doc in db.transactions.find(
            {"user_id": user["_id"], "date": {"$gte": to_utc_datetime(min(dates)), "$lte": to_utc_datetime(max(dates))}},
            {"date": 1, "title": 1, "amount": 1, "type": 1},
        ):
            stored[_dup_key(doc["date"].date(), doc["title"], doc["amount"], doc["type"])] += 1
        for _, tx in valid:
            key = _dup_key(tx.date, tx.title, tx.amount, tx.type)
            if stored[key] > 0:
                stored[key] -= 1
                skipped += 1
            else:
                to_insert.append({"user_id": user["_id"], **_to_doc(tx)})
        if to_insert:
            await db.transactions.insert_many(to_insert)

    errors.sort(key=lambda e: e["row"])
    return {
        "created": len(to_insert),
        "skipped_duplicates": skipped,
        "created_categories": created_categories,
        "errors": errors,
    }


def _dup_key(d: date, title: str, amount: float, tx_type: str) -> tuple:
    return (d, title.strip().lower(), round(amount, 2), tx_type)


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
