from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.database import get_db
from app.deps import CurrentUser
from app.schemas import TokenOut, UserCreate, UserLogin, UserOut
from app.security import create_access_token, hash_password, verify_password
from app.serializers import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])

DEFAULT_CATEGORIES = {
    "expense": ["Food", "Transport", "Shopping", "Bills", "Rent", "Entertainment", "Health", "Education", "Other"],
    "income": ["Salary", "Freelance", "Investments", "Gifts", "Other"],
}


async def _seed_default_categories(user_id: ObjectId) -> None:
    docs = [
        {"user_id": user_id, "name": name, "type": tx_type}
        for tx_type, names in DEFAULT_CATEGORIES.items()
        for name in names
    ]
    await get_db().categories.insert_many(docs)


def _token_response(user: dict) -> dict:
    return {
        "access_token": create_access_token(str(user["_id"])),
        "token_type": "bearer",
        "user": user_out(user),
    }


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate):
    user = {
        "name": data.name,
        "email": data.email.lower(),
        "password_hash": hash_password(data.password),
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = await get_db().users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user["_id"] = result.inserted_id
    await _seed_default_categories(result.inserted_id)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
async def login(data: UserLogin):
    user = await get_db().users.find_one({"email": data.email.lower()})
    if not verify_password(data.password, user["password_hash"] if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return _token_response(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user_out(user)
