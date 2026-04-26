"""Drop avg_price_per_oz_usd column from tea_profiles

Revision ID: 195fc95e0ff3
Revises: 706ea5a4e4f3
Create Date: 2026-04-22 14:47:03.204294

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '195fc95e0ff3'
down_revision: Union[str, Sequence[str], None] = '706ea5a4e4f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Drop the average price per ounce column going forward.
    op.drop_column('tea_profiles', 'avg_price_per_oz_usd')


def downgrade() -> None:
    """Downgrade schema."""
    
    op.add_column('tea_profiles', 
        sa.Column('avg_price_per_oz_usd', sa.Numeric(7, 2), nullable=True))
