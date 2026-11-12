"""Paused campaign drafts with calendar schedules."""
from alembic import op
import sqlalchemy as sa

revision = '006_campaigns'
down_revision = '005_gallery'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('campaigns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request_key', sa.String(36), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=False),
        sa.Column('destination_title', sa.String(255), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('owner_id', 'request_key', name='uq_campaign_owner_request'))
    op.create_index('ix_campaigns_owner_id', 'campaigns', ['owner_id'])

def downgrade():
    op.drop_table('campaigns')
