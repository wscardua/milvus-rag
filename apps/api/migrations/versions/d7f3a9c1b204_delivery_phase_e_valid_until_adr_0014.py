"""delivery_phase e valid_until em document (ADR-0014)

Revision ID: d7f3a9c1b204
Revises: cc34b9227367
Create Date: 2026-07-10 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd7f3a9c1b204'
down_revision: Union[str, None] = 'cc34b9227367'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ambos nullable, sem backfill — documentos existentes ficam com NULL (ADR-0014).
    op.add_column('document', sa.Column('delivery_phase', sa.String(length=60), nullable=True))
    op.add_column('document', sa.Column('valid_until', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('document', 'valid_until')
    op.drop_column('document', 'delivery_phase')
