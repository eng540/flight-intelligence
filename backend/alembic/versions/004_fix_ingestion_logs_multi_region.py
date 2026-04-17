"""Fix ingestion_logs for multi-region parallel intelligence tracking

Revision ID: 004
Revises: 003
Create Date: 2026-04-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── 1. إزالة القيد الفريد الأحادي على target_date ───
    # Migration 003 أنشأ فهرساً فريداً نعرف اسمه
    op.drop_index('ix_ingestion_logs_target_date', table_name='ingestion_logs')
    
    # إزالة قيد UniqueConstraint التلقائي (PostgreSQL يُنشئه باسم ثابت)
    op.execute("""
        ALTER TABLE ingestion_logs 
        DROP CONSTRAINT IF EXISTS ingestion_logs_target_date_key
    """)
    
    # ─── 2. إضافة أعمدة التتبع الاستخباراتي ───
    op.add_column(
        'ingestion_logs',
        sa.Column('task_id', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'ingestion_logs',
        sa.Column('start_date', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'ingestion_logs',
        sa.Column('end_date', sa.String(length=20), nullable=True)
    )
    
    # ─── 3. إعادة إنشاء الفهارس بشكل صحيح ───
    # فهرس غير فريد على target_date للبحث السريع
    op.create_index(
        'ix_ingestion_logs_target_date',
        'ingestion_logs',
        ['target_date'],
        unique=False
    )
    
    # فهرس على task_id لتتبع مهام Celery
    op.create_index(
        'ix_ingestion_logs_task_id',
        'ingestion_logs',
        ['task_id'],
        unique=False
    )
    
    # ─── 4. القيد الفريد المركب: كل يوم + كل منطقة = سجل واحد ───
    op.create_unique_constraint(
        'uq_ingestion_target_region',
        'ingestion_logs',
        ['target_date', 'region']
    )


def downgrade() -> None:
    op.drop_constraint('uq_ingestion_target_region', 'ingestion_logs', type_='unique')
    op.drop_index('ix_ingestion_logs_task_id', table_name='ingestion_logs')
    op.drop_index('ix_ingestion_logs_target_date', table_name='ingestion_logs')
    op.drop_column('ingestion_logs', 'end_date')
    op.drop_column('ingestion_logs', 'start_date')
    op.drop_column('ingestion_logs', 'task_id')
    
    # إعادة الفهرس الفريد القديم
    op.create_index(
        'ix_ingestion_logs_target_date',
        'ingestion_logs',
        ['target_date'],
        unique=True
    )
