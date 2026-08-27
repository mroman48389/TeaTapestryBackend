"""change user_id type to UUID in dsar_logs table

Revision ID: 07964e312d45
Revises: 191d2af62a88
Create Date: 2026-08-27 14:06:27.344585

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07964e312d45'
down_revision: Union[str, Sequence[str], None] = '191d2af62a88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert id VARCHAR → UUID
    op.alter_column(
        "dsar_logs",
        "id",
        existing_type=sa.VARCHAR(),
        type_=sa.UUID(),
        existing_nullable=False,
        postgresql_using="id::uuid"
    )

    # Convert user_id VARCHAR → UUID
    op.alter_column(
        "dsar_logs",
        "user_id",
        existing_type=sa.VARCHAR(),
        type_=sa.UUID(),
        existing_nullable=False,
        postgresql_using="user_id::uuid"
    )

    # Now that types match, create the FK
    op.create_foreign_key(
        "fk_dsar_logs_user_id",     # explicit name
        "dsar_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    # Drop the FK we created
    op.drop_constraint(
        "fk_dsar_logs_user_id",
        "dsar_logs",
        type_="foreignkey"
    )

    # Convert user_id back to VARCHAR
    op.alter_column(
        "dsar_logs",
        "user_id",
        existing_type=sa.UUID(),
        type_=sa.VARCHAR(),
        existing_nullable=False
    )

    # Convert id back to VARCHAR
    op.alter_column(
        "dsar_logs",
        "id",
        existing_type=sa.UUID(),
        type_=sa.VARCHAR(),
        existing_nullable=False
    )
