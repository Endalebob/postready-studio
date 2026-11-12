"""Durable, explicitly requested campaign preparations."""
from alembic import op
import sqlalchemy as sa
revision = '007_preparations'
down_revision = '006_campaigns'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('campaign_preparations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request_key', sa.String(36), nullable=False),
        sa.Column('ad_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('assets', sa.JSON(), nullable=False),
        sa.Column('output', sa.JSON(), nullable=False),
        sa.Column('detail', sa.String(300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('owner_id', 'request_key', name='uq_preparation_owner_request'))
    for column in ('owner_id', 'campaign_id', 'status'):
        op.create_index('ix_campaign_preparations_'+column, 'campaign_preparations', [column])

def downgrade():
    op.drop_table('campaign_preparations')
