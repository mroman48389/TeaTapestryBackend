"""fix timezone default for password_confirmations.created_at

Revision ID: ee67b068655c
Revises: cbf8c4badc89
Create Date: 2026-09-10 13:54:17.923892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee67b068655c'
down_revision: Union[str, Sequence[str], None] = 'cbf8c4badc89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "password_confirmations",
        "created_at",
        server_default=sa.text("CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
    )

def downgrade() -> None:
    op.alter_column(
        "password_confirmations",
        "created_at",
        server_default=sa.text("CURRENT_TIMESTAMP")
    )
