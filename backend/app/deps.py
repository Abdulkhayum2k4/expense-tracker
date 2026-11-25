from typing import Annotated

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_db
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user_id = decode_access_token(credentials.credentials)
    if user_id is None or not ObjectId.is_valid(user_id):
        raise unauthorized
    user = await get_db().users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]


def parse_object_id(value: str, what: str = "Resource") -> ObjectId:
    """Turn a path id into an ObjectId; an invalid id is treated as not found."""
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=404, detail=f"{what} not found")
    return ObjectId(value)
