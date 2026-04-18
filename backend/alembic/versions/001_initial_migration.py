"""Initial Intelligence Schema

Revision ID: 001
Revises: 
Create Date: 2024-05-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create ENUM types for PostgreSQL
    job_mode_enum = postgresql.ENUM('HISTORICAL', 'CONTINUOUS', 'REALTIME', name='job_mode_enum')
    job_mode_enum.create(op.get_bind())
    
    job_status_enum = postgresql.ENUM('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', name='job_status_enum')
    job_status_enum.create(op.get_bind())

    # 2. Create Countries Table
    op.create_table(
        'countries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('iso_code', sa.String(length=3), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('iso_code')
    )
    op.create_index(op.f('ix_countries_name'), 'countries', ['name'], unique=False)

    # 3. Create Airlines Table
    op.create_table(
        'airlines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('icao24', sa.String(length=6), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('callsign_prefix', sa.String(length=10), nullable=True),
        sa.Column('country_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('icao24')
    )
    op.create_index('idx_airline_icao24_name', 'airlines', ['icao24', 'name'], unique=False)

    # 4. Create Flights Table (Source of Truth)
    op.create_table(
        'flights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('icao24', sa.String(length=6), nullable=False),
        sa.Column('callsign', sa.String(length=20), nullable=True),
        sa.Column('airline_id', sa.Integer(), nullable=True),
        sa.Column('origin_country', sa.String(length=100), nullable=True),
        sa.Column('first_seen', sa.BigInteger(), nullable=False),
        sa.Column('last_seen', sa.BigInteger(), nullable=False),
        sa.Column('est_departure_airport', sa.String(length=4), nullable=True),
        sa.Column('est_arrival_airport', sa.String(length=4), nullable=True),
        sa.Column('ingestion_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('unique_flight_id', sa.String(length=100), nullable=False),
        sa.Column('trajectory', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['airline_id'], ['airlines.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('unique_flight_id')
    )
    op.create_index(op.f('ix_flights_icao24'), 'flights', ['icao24'], unique=False)
    op.create_index(op.f('ix_flights_callsign'), 'flights', ['callsign'], unique=False)
    op.create_index('idx_flight_time_range', 'flights', ['first_seen', 'last_seen'], unique=False)
    op.create_index('idx_flight_airports', 'flights', ['est_departure_airport', 'est_arrival_airport'], unique=False)

    # 5. Create Flight Events Table (Intelligence Layer)
    op.create_table(
        'flight_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flight_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['flight_id'], ['flights.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_flight_events_flight_id'), 'flight_events', ['flight_id'], unique=False)
    op.create_index(op.f('ix_flight_events_event_type'), 'flight_events', ['event_type'], unique=False)

    # 6. Create Ingestion Jobs Table (Audit Layer)
    op.create_table(
        'ingestion_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=100), nullable=True),
        sa.Column('mode', postgresql.ENUM(name='job_mode_enum', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM(name='job_status_enum', create_type=False), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('records_fetched', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ingestion_jobs_mode'), 'ingestion_jobs', ['mode'], unique=False)
    op.create_index(op.f('ix_ingestion_jobs_status'), 'ingestion_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('ingestion_jobs')
    op.drop_table('flight_events')
    op.drop_table('flights')
    op.drop_table('airlines')
    op.drop_table('countries')
    
    # Drop ENUMs
    postgresql.ENUM(name='job_status_enum').drop(op.get_bind())
    postgresql.ENUM(name='job_mode_enum').drop(op.get_bind())