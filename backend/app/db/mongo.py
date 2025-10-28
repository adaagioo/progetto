# backend/app/db/mongo.py
from __future__ import annotations

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import settings

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    assert _client is not None, "Mongo client not initialized. Call init_mongo() on startup."
    return _client


def get_db():
    client = get_client()
    return client[settings.MONGO_DB_NAME]


async def init_mongo() -> None:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI)
        # NOTE: Optional ping to verify connectivity on startup
        # await _client.admin.command("ping")


async def close_mongo() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
