"""add account lockout fields

Revision ID: a1c4e8f0d7b3
Revises: f3a7c1d9b2e6
Create Date: 2026-07-07 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e8f0d7b3'
down_revision: Union[str, Sequence[str], None] = 'f3a7c1d9b2e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'accounts',
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column('accounts', sa.Column('locked_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('accounts', 'locked_until')
    op.drop_column('accounts', 'failed_login_attempts')
