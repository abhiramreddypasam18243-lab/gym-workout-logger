"""Database initialization script run before starting the backend server (AC-97, AC-103).

Ensures:
1. Database tables are migrated to the latest Alembic revision; a failed migration stops startup.
2. Exercise and food catalogues are seeded if not present.
3. The synthetic demo account exists, only when DEMO_MODE is true.
"""

import asyncio
import logging

from alembic.config import Config
from sqlalchemy import select

from alembic import command
from app.config import settings
from app.database import async_session_factory
from app.demo_user import DEMO_EMAIL, create_demo_user
from app.models.user import User
from app.models.workout import Exercise
from app.seed.loader import run_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init_db")


def run_migrations() -> None:
    """Run Alembic migrations up to head."""
    logger.info("Applying database migrations with Alembic...")
    command.upgrade(Config("alembic.ini"), "head")
    logger.info("Alembic migrations completed successfully.")


async def seed_data() -> None:
    """Ensure schema exists, seed exercises/foods, and initialize demo user."""
    async with async_session_factory() as session:
        # Check if catalogue is already seeded
        res = await session.execute(select(Exercise).limit(1))
        has_exercises = res.scalar_one_or_none() is not None

        if not has_exercises:
            logger.info("Seeding catalogue with standard exercises and USDA food dataset...")
            await run_seed(session)
            logger.info("Catalogue seed complete.")
        else:
            logger.info("Catalogue already populated.")

        if not settings.DEMO_MODE:
            logger.info("DEMO_MODE is off; skipping synthetic demo user.")
            return

        # Check if demo user exists
        user_res = await session.execute(select(User).where(User.email == DEMO_EMAIL))
        demo_user = user_res.scalar_one_or_none()
        if not demo_user:
            logger.info("Initializing synthetic demo user (%s)...", DEMO_EMAIL)
            await create_demo_user(session, num_sessions=50, quick_mode=True)
            logger.info("Synthetic demo user created.")
        else:
            logger.info("Synthetic demo user already present.")


def main() -> None:
    masked_target = settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url
    logger.info("Connecting to database target: %s", masked_target)
    run_migrations()
    asyncio.run(seed_data())
    logger.info("Database initialization finished successfully.")


if __name__ == "__main__":
    main()
