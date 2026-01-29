# migrations/versions/20240129_0100_add_fase3_tables.py
"""Add FASE 3 tables: tenant_configs and integration_logs

Revision ID: 20240129_0100
Revises: previous_migration_id
Create Date: 2024-01-29 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240129_0100'
down_revision = 'previous_migration_id'  # Update with your actual previous migration
branch_labels = None
depends_on = None


def upgrade():
    # Create tenant_configs table
    op.create_table('tenant_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('allow_overpicking', sa.Boolean(), nullable=True, default=False),
        sa.Column('allow_partial_picking', sa.Boolean(), nullable=True, default=True),
        sa.Column('auto_reserve_stock', sa.Boolean(), nullable=True, default=True),
        sa.Column('require_picking_confirmation', sa.Boolean(), nullable=True, default=True),
        sa.Column('default_warehouse_id', sa.Integer(), nullable=True),
        sa.Column('dolibarr_api_url', sa.String(length=500), nullable=True),
        sa.Column('dolibarr_api_key', sa.String(length=200), nullable=True),
        sa.Column('dolibarr_warehouse_id', sa.Integer(), nullable=True),
        sa.Column('webhook_url', sa.String(length=500), nullable=True),
        sa.Column('notify_on_picking_complete', sa.Boolean(), nullable=True, default=True),
        sa.Column('notify_on_stock_difference', sa.Boolean(), nullable=True, default=True),
        sa.Column('notify_on_integration_error', sa.Boolean(), nullable=True, default=True),
        sa.Column('brand_name', sa.String(length=100), nullable=True),
        sa.Column('brand_logo_url', sa.String(length=500), nullable=True),
        sa.Column('brand_primary_color', sa.String(length=7), nullable=True),
        sa.Column('max_retry_attempts', sa.Integer(), nullable=True, default=3),
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=True, default=60),
        sa.Column('audit_retention_days', sa.Integer(), nullable=True, default=90),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id')
    )
    
    # Create integration_logs table
    op.create_table('integration_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add discrepancy_synced column to picking_items
    op.add_column('picking_items', 
        sa.Column('discrepancy_synced', sa.Boolean(), nullable=True, default=False)
    )
    
    # Create indexes
    op.create_index('ix_tenant_configs_tenant_id', 'tenant_configs', ['tenant_id'], unique=True)
    op.create_index('ix_integration_logs_tenant_id', 'integration_logs', ['tenant_id'])
    op.create_index('ix_integration_logs_status', 'integration_logs', ['status'])
    op.create_index('ix_integration_logs_created_at', 'integration_logs', ['created_at'])
    op.create_index('ix_integration_logs_action', 'integration_logs', ['action'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_integration_logs_action', table_name='integration_logs')
    op.drop_index('ix_integration_logs_created_at', table_name='integration_logs')
    op.drop_index('ix_integration_logs_status', table_name='integration_logs')
    op.drop_index('ix_integration_logs_tenant_id', table_name='integration_logs')
    op.drop_index('ix_tenant_configs_tenant_id', table_name='tenant_configs')
    
    # Drop columns
    op.drop_column('picking_items', 'discrepancy_synced')
    
    # Drop tables
    op.drop_table('integration_logs')
    op.drop_table('tenant_configs')