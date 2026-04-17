"""Add ingestion_logs table

Revision ID: 003
Revises: 002
Create Date: 2024-05-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'ingestion_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('target_date', sa.String(length=10), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('records_fetched', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('target_date')
    )
    op.create_index(op.f('ix_ingestion_logs_target_date'), 'ingestion_logs', ['target_date'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_ingestion_logs_target_date'), table_name='ingestion_logs')
    op.drop_table('ingestion_logs')