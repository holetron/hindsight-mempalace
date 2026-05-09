"""Add layer column to memory_units for hierarchical memory filtering (ADR-145)

Revision ID: aa2_layer
Revises: aa1_room_hall
Create Date: 2026-05-09

Adds layer column (memory priority L0-L3) to memory_units.
Default is L2 (working memory). Part of MemPalace hierarchical memory architecture.

This column was referenced in models.py and the retain engine since commit 99f29ed5
but the migration was accidentally omitted from aa1_add_room_hall_to_memory_units.py.
"""

from collections.abc import Sequence

from alembic import context, op

revision: str = "aa2_layer"
down_revision: str | Sequence[str] | None = "aa1_room_hall"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _get_schema_prefix() -> str:
    """Get schema prefix for table names (required for multi-tenant support)."""
    schema = context.config.get_main_option("target_schema")
    return f'"{schema}.' if schema else ""


def upgrade() -> None:
    schema = _get_schema_prefix()

    # Layer: memory priority (L0=ephemeral, L1=short-term, L2=working, L3=long-term)
    op.execute(
        f"ALTER TABLE {schema}memory_units ADD COLUMN IF NOT EXISTS layer TEXT DEFAULT 'L2'"
    )

    # Index for layer filtering (used in recall with max_layer parameter)
    op.execute(
        f"CREATE INDEX IF NOT EXISTS idx_memory_units_layer "
        f"ON {schema}memory_units (bank_id, layer) WHERE layer IS NOT NULL"
    )


def downgrade() -> None:
    schema = _get_schema_prefix()
    op.execute(f"DROP INDEX IF EXISTS {schema}idx_memory_units_layer")
    op.execute(f"ALTER TABLE {schema}memory_units DROP COLUMN IF EXISTS layer")