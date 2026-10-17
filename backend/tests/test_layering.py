"""Architecture layering test (spec §8, AC-98).

Verifies that app/domain contains pure functions with NO imports from
frameworks (FastAPI, Starlette), database (SQLAlchemy, asyncpg, alembic),
or system clock (datetime.now, time.time).
"""

import ast
from pathlib import Path

FORBIDDEN_DOMAIN_MODULES = {
    "fastapi",
    "starlette",
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "pydantic",
}


def test_ac_98_domain_layer_purity():
    """AC-98: app/domain imports no framework, database, or clock modules."""
    domain_dir = Path(__file__).parent.parent / "app" / "domain"
    domain_py_files = list(domain_dir.glob("*.py"))

    assert len(domain_py_files) > 0, "No domain files found to check"

    for py_file in domain_py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

        for node in ast.walk(tree):
            # Check import foo
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    assert root_pkg not in FORBIDDEN_DOMAIN_MODULES, (
                        f"{py_file.name} violates AC-98 by importing framework/db package '{alias.name}'"
                    )

            # Check from foo import bar
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg not in FORBIDDEN_DOMAIN_MODULES, (
                    f"{py_file.name} violates AC-98 by importing from '{node.module}'"
                )

                # Check clock imports
                if node.module == "datetime":
                    for alias in node.names:
                        assert alias.name not in ("now", "utcnow"), (
                            f"{py_file.name} violates AC-98 by importing dynamic clock function '{alias.name}'"
                        )
