from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.database import get_db
from app.deps import CurrentUser
from app.rate_limit import limiter
from app.schemas import AccountDelete, PasswordChange, TokenOut, UserCreate, UserLogin, UserOut, UserUpdate
from app.security import AUTH_COOKIE, create_access_token, hash_password, verify_password
from app.serializers import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])

DEFAULT_CATEGORIES = {
    "expense": ["Food", "Transport", "Shopping", "Bills", "Rent", "Entertainment", "Health", "Education", "Other"],
    "income": ["Salary", "Freelance", "Investments", "Gifts", "Other"],
}

# Every collection that holds per-user data; used when an account is deleted.
USER_DATA_COLLECTIONS = ("transactions", "categories", "budgets", "goals")


async def _seed_default_categories(user_id: ObjectId) -> None:
    docs = [
        {"user_id": user_id, "name": name, "type": tx_type}
        for tx_type, names in DEFAULT_CATEGORIES.items()
        for name in names
    ]
    await get_db().categories.insert_many(docs)


def _start_session(response: Response, user: dict) -> dict:
    """Set the httpOnly auth cookie and build the login response.

    The token is also returned in the body for API clients (Swagger, Postman);
    the web app ignores it and relies on the cookie.
    """
    token = create_access_token(str(user["_id"]), user.get("token_version", 0))
    response.set_cookie(
        AUTH_COOKIE,
        token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api",
    )
    return {"access_token": token, "token_type": "bearer", "user": user_out(user)}


def _end_session() -> Response:
    """An empty 204 response that clears the auth cookie."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(AUTH_COOKIE, path="/api", httponly=True, secure=settings.cookie_secure, samesite="lax")
    return response


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(request: Request, response: Response, data: UserCreate):
    user = {
        "name": data.name,
        "email": data.email.lower(),
        "password_hash": hash_password(data.password),
        "token_version": 0,
        "currency": "INR",
        "budget_alerts": True,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = await get_db().users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user["_id"] = result.inserted_id
    await _seed_default_categories(result.inserted_id)
    return _start_session(response, user)


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")
async def login(request: Request, response: Response, data: UserLogin):
    user = await get_db().users.find_one({"email": data.email.lower()})
    if not verify_password(data.password, user["password_hash"] if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return _start_session(response, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    return _end_session()


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user_out(user)


@router.patch("/me", response_model=UserOut)
async def update_me(data: UserUpdate, user: CurrentUser):
    changes = data.model_dump(exclude_none=True)
    if not changes:
        return user_out(user)
    updated = await get_db().users.find_one_and_update(
        {"_id": user["_id"]}, {"$set": changes}, return_document=True
    )
    return user_out(updated)


@router.put("/password", response_model=TokenOut)
@limiter.limit("5/minute")
async def change_password(request: Request, response: Response, data: PasswordChange, user: CurrentUser):
    if not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if data.new_password == data.current_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must be different from the current one")
    # Bumping token_version signs out every other session; this one gets a fresh token.
    updated = await get_db().users.find_one_and_update(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(data.new_password)}, "$inc": {"token_version": 1}},
        return_document=True,
    )
    return _start_session(response, updated)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def delete_account(request: Request, data: AccountDelete, user: CurrentUser):
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is incorrect")
    db = get_db()
    for name in USER_DATA_COLLECTIONS:
        await db[name].delete_many({"user_id": user["_id"]})
    await db.users.delete_one({"_id": user["_id"]})
    return _end_session()
