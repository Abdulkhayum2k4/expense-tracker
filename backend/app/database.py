from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.config import settings

_client: AsyncMongoClient | None = None


def get_db() -> AsyncDatabase:
    if _client is None:
        raise RuntimeError("Database is not connected")
    return _client[settings.mongodb_db]


async def connect() -> None:
    global _client
    # tz_aware=True: datetimes come back as UTC-aware objects
    _client = AsyncMongoClient(settings.mongodb_url, tz_aware=True)
    await _client.admin.command("ping")
    await _create_indexes()


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def _create_indexes() -> None:
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.transactions.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
    await db.transactions.create_index([("user_id", ASCENDING), ("category", ASCENDING)])
    await db.categories.create_index(
        [("user_id", ASCENDING), ("type", ASCENDING), ("name", ASCENDING)], unique=True
    )
    await db.budgets.create_index(
        [("user_id", ASCENDING), ("year", ASCENDING), ("month", ASCENDING), ("category", ASCENDING)],
        unique=True,
    )
