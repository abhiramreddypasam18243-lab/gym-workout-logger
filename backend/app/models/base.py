"""SQLAlchemy declarative base for all models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models.

    All models inherit from this. Alembic uses Base.metadata
    for autogenerate.
    """

    pass
