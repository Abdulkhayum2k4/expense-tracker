from typing import Annotated

from bson import ObjectId
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_db
from app.security import AUTH_COOKIE, decode_access_token

# Bearer is still accepted so Swagger's "Authorize" button and Postman work.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials if credentials else request.cookies.get(AUTH_COOKIE)
    if not token:
        raise unauthorized
    claims = decode_access_token(token)
    if claims is None or not ObjectId.is_valid(claims.user_id):
        raise unauthorized
    user = await get_db().users.find_one({"_id": ObjectId(claims.user_id)})
    # A password change bumps token_version, which revokes every token issued before it.
    if user is None or user.get("token_version", 0) != claims.version:
        raise unauthorized
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]


def parse_object_id(value: str, what: str = "Resource") -> ObjectId:
    """Turn a path id into an ObjectId; an invalid id is treated as not found."""
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=404, detail=f"{what} not found")
    return ObjectId(value)
