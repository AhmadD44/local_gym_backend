"""One-off generator for the initial Alembic migration.

Compiles CREATE TABLE / CREATE INDEX DDL directly against the PostgreSQL
dialect (no live database connection required — dialect compilation is
pure Python) from the SQLAlchemy models, plus explicit CREATE TYPE
statements for the native enums. This keeps the initial migration exactly
in sync with app/models/*.py without requiring a running Postgres in this
environment; normal Alembic --autogenerate remains the right tool for all
*subsequent* migrations once a database is available.

Usage: python -m scripts._render_initial_migration > migrations/versions/0001_initial_schema.py
"""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import app.models as models
from app.models import enums as enums_module

DIALECT = postgresql.dialect()


def _enum_classes():
    for name in dir(enums_module):
        obj = getattr(enums_module, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, __import__("enum").Enum)
            and obj is not __import__("enum").Enum
        ):
            yield obj


def _snake(name: str) -> str:
    import re

    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def render() -> str:
    md = models.Base.metadata
    tables = md.sorted_tables

    enum_upgrades = []
    enum_downgrades = []
    seen_enum_names = set()
    for col in (c for t in tables for c in t.columns):
        col_type = col.type
        if isinstance(col_type, postgresql.ENUM) or (hasattr(col_type, "enums") and hasattr(col_type, "name")):
            enum_name = getattr(col_type, "name", None)
            if not enum_name or enum_name in seen_enum_names:
                continue
            seen_enum_names.add(enum_name)
            values = ", ".join(f"'{v}'" for v in col_type.enums)
            enum_upgrades.append(f'    op.execute("CREATE TYPE {enum_name} AS ENUM ({values})")')
            enum_downgrades.append(f'    op.execute("DROP TYPE IF EXISTS {enum_name}")')

    table_upgrades = []
    table_downgrades = []
    for table in tables:
        ddl = str(CreateTable(table).compile(dialect=DIALECT)).strip()
        table_upgrades.append(f'    op.execute("""\n{ddl}\n""")')
        for index in table.indexes:
            idx_ddl = str(CreateIndex(index).compile(dialect=DIALECT)).strip()
            table_upgrades.append(f'    op.execute("""{idx_ddl}""")')

    for table in reversed(tables):
        table_downgrades.append(f'    op.execute("DROP TABLE IF EXISTS {table.name} CASCADE")')

    upgrade_body = "\n".join(enum_upgrades) + "\n\n" + "\n".join(table_upgrades)
    downgrade_body = "\n".join(table_downgrades) + "\n\n" + "\n".join(enum_downgrades)

    return f'''"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-06

"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
{upgrade_body}


def downgrade() -> None:
{downgrade_body}
'''


if __name__ == "__main__":
    print(render())
