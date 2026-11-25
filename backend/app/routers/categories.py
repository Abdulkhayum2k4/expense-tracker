from fastapi import APIRouter, HTTPException, Response, status
from pymongo.errors import DuplicateKeyError

from app.database import get_db
from app.deps import CurrentUser, parse_object_id
from app.schemas import CategoryIn, CategoryOut, TxType
from app.serializers import category_out

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories(user: CurrentUser, type: TxType | None = None):
    query: dict = {"user_id": user["_id"]}
    if type:
        query["type"] = type
    cursor = get_db().categories.find(query).sort([("type", 1), ("name", 1)])
    return [category_out(doc) async for doc in cursor]


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryIn, user: CurrentUser):
    doc = {"user_id": user["_id"], "name": data.name, "type": data.type}
    try:
        result = await get_db().categories.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, f"You already have a {data.type} category named '{data.name}'")
    doc["_id"] = result.inserted_id
    return category_out(doc)


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(category_id: str, data: CategoryIn, user: CurrentUser):
    db = get_db()
    oid = parse_object_id(category_id, "Category")
    existing = await db.categories.find_one({"_id": oid, "user_id": user["_id"]})
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    if data.type != existing["type"]:
        in_use = await db.transactions.count_documents(
            {"user_id": user["_id"], "type": existing["type"], "category": existing["name"]}, limit=1
        )
        if in_use:
            raise HTTPException(status.HTTP_409_CONFLICT, "Can't change the type of a category that has transactions")

    try:
        await db.categories.update_one({"_id": oid}, {"$set": {"name": data.name, "type": data.type}})
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, f"You already have a {data.type} category named '{data.name}'")

    # Transactions and budgets reference categories by name, so carry a rename over to them.
    if data.name != existing["name"]:
        await db.transactions.update_many(
            {"user_id": user["_id"], "type": existing["type"], "category": existing["name"]},
            {"$set": {"category": data.name}},
        )
        if existing["type"] == "expense":
            await db.budgets.update_many(
                {"user_id": user["_id"], "category": existing["name"]},
                {"$set": {"category": data.name}},
            )
    return {"id": category_id, "name": data.name, "type": data.type}


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: str, user: CurrentUser):
    db = get_db()
    oid = parse_object_id(category_id, "Category")
    existing = await db.categories.find_one({"_id": oid, "user_id": user["_id"]})
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    in_use = await db.transactions.count_documents(
        {"user_id": user["_id"], "type": existing["type"], "category": existing["name"]}, limit=1
    )
    if in_use:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This category has transactions. Move or delete them before deleting the category.",
        )
    await db.categories.delete_one({"_id": oid})
    if existing["type"] == "expense":
        await db.budgets.delete_many({"user_id": user["_id"], "category": existing["name"]})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
