"""remove server_default from password_confirmations.created_at

Revision ID: 2d77b4d8fbe1
Revises: ee67b068655c
Create Date: 2026-09-10 13:57:04.326065

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d77b4d8fbe1'
down_revision: Union[str, Sequence[str], None] = 'ee67b068655c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "password_confirmations",
        "created_at",
        server_default=None
    )

def downgrade() -> None:
    op.alter_column(
        "password_confirmations",
        "created_at",
        server_default=sa.text("CURRENT_TIMESTAMP")
    )
