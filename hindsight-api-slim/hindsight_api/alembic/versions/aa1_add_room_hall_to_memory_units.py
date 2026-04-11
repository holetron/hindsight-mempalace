"""Add room and hall columns to memory_units for hierarchical filtering (ADR-145)

Revision ID: aa1_room_hall
Revises: z1u2v3w4x5y6
Create Date: 2026-04-11

Adds room (topic) and hall (knowledge type) columns to memory_units.
Room/Hall taxonomy enables pre-semantic filtering for +34% recall accuracy
(MemPalace benchmark: 60.9% flat → 94.8% with Room+Hall filtering).
"""

from collections.abc import Sequence

from alembic import context, op

revision: str = "aa1_room_hall"
down_revision: str | Sequence[str] | None = "z1u2v3w4x5y6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _get_schema_prefix() -> str:
    """Get schema prefix for table names (required for multi-tenant support)."""
    schema = context.config.get_main_option("target_schema")
    return f'"{schema}".' if schema else ""


def upgrade() -> None:
    schema = _get_schema_prefix()

    # Room: topic classification (what the memory is about)
    op.execute(f"ALTER TABLE {schema}memory_units ADD COLUMN IF NOT EXISTS room TEXT")

    # Hall: knowledge type classification (what kind of knowledge)
    op.execute(f"ALTER TABLE {schema}memory_units ADD COLUMN IF NOT EXISTS hall TEXT")

    # Indexes for filtering BEFORE semantic search
    op.execute(
        f"CREATE INDEX IF NOT EXISTS idx_memory_units_room "
        f"ON {schema}memory_units (bank_id, room) WHERE room IS NOT NULL"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS idx_memory_units_hall "
        f"ON {schema}memory_units (bank_id, hall) WHERE hall IS NOT NULL"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS idx_memory_units_room_hall "
        f"ON {schema}memory_units (bank_id, room, hall) WHERE room IS NOT NULL AND hall IS NOT NULL"
    )


def downgrade() -> None:
    schema = _get_schema_prefix()
    op.execute(f"DROP INDEX IF EXISTS {schema}idx_memory_units_room_hall")
    op.execute(f"DROP INDEX IF EXISTS {schema}idx_memory_units_hall")
    op.execute(f"DROP INDEX IF EXISTS {schema}idx_memory_units_room")
    op.execute(f"ALTER TABLE {schema}memory_units DROP COLUMN IF EXISTS hall")
    op.execute(f"ALTER TABLE {schema}memory_units DROP COLUMN IF EXISTS room")
