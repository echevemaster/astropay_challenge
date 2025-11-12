"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('product', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('custom_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('search_content', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_product_currency', 'transactions', ['product', 'currency'], unique=False)
    op.create_index('idx_type_status', 'transactions', ['transaction_type', 'status'], unique=False)
    op.create_index('idx_user_created', 'transactions', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_transactions_created_at'), 'transactions', ['created_at'], unique=False)
    op.create_index(op.f('ix_transactions_currency'), 'transactions', ['currency'], unique=False)
    op.create_index(op.f('ix_transactions_product'), 'transactions', ['product'], unique=False)
    op.create_index(op.f('ix_transactions_status'), 'transactions', ['status'], unique=False)
    op.create_index(op.f('ix_transactions_transaction_type'), 'transactions', ['transaction_type'], unique=False)
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transactions_user_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_transaction_type'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_status'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_product'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_currency'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_created_at'), table_name='transactions')
    op.drop_index('idx_user_created', table_name='transactions')
    op.drop_index('idx_type_status', table_name='transactions')
    op.drop_index('idx_product_currency', table_name='transactions')
    op.drop_table('transactions')

