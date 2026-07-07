"""add 2fa fields and backup_codes table

Revision ID: b7d2f4a6c9e1
Revises: a1c4e8f0d7b3
Create Date: 2026-07-07 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2f4a6c9e1'
down_revision: Union[str, Sequence[str], None] = 'a1c4e8f0d7b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('accounts', sa.Column('totp_secret', sa.String(), nullable=True))
    op.add_column(
        'accounts',
        sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default='false'),
    )

    op.create_table('backup_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('code_hash', sa.String(), nullable=False),
    sa.Column('used_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backup_codes_id'), 'backup_codes', ['id'], unique=False)
    op.create_index(op.f('ix_backup_codes_account_id'), 'backup_codes', ['account_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_backup_codes_account_id'), table_name='backup_codes')
    op.drop_index(op.f('ix_backup_codes_id'), table_name='backup_codes')
    op.drop_table('backup_codes')
    op.drop_column('accounts', 'totp_enabled')
    op.drop_column('accounts', 'totp_secret')
