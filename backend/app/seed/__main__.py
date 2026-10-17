"""CLI entrypoint for running the catalogue seed command: python -m app.seed (D4, AC-106)."""

import asyncio

from app.database import async_session_factory
from app.seed.loader import run_seed


async def main() -> None:
    print("Starting catalogue seed...")
    async with async_session_factory() as session:
        results = await run_seed(session)
        print("Seed completed successfully:")
        print(f"  Exercises inserted: {results['exercises_inserted']}")
        print(f"  Foods inserted:     {results['foods_inserted']}")
        print(f"  Recipes inserted:   {results['recipes_inserted']}")


if __name__ == "__main__":
    asyncio.run(main())
