"""Add trajectory column to flights

Revision ID: 002
Revises: 001
Create Date: 2024-05-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # إضافة عمود trajectory كـ JSONB
    op.add_column('flights', sa.Column('trajectory', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade() -> None:
    op.drop_column('flights', 'trajectory')