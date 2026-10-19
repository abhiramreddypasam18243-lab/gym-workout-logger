"""Shared test database helpers: every DB test runs against PostgreSQL (ag.md project rules).

Set TEST_DATABASE_URL to point at a disposable PostgreSQL database; its schema is
dropped and recreated for each test.
"""

import os

from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.models.base import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://gymlogger:test_password_1234@localhost:5432/gymlogger",
)


def create_test_engine() -> AsyncEngine:
    """Engine for the disposable PostgreSQL test database."""
    return create_async_engine(TEST_DATABASE_URL, echo=False)


def reset_schema(conn: Connection) -> None:
    """Drop and recreate every table so each test starts from an empty schema."""
    Base.metadata.drop_all(conn)
    Base.metadata.create_all(conn)
