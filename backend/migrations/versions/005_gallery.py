"""Persistent owner-approved campaign gallery."""
from alembic import op
import sqlalchemy as sa
revision='005_gallery'
down_revision='004_videos'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('gallery_assets',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('request_key',sa.String(36),nullable=False),
        sa.Column('storage_key',sa.String(200),nullable=False),
        sa.Column('details',sa.JSON(),nullable=False),sa.Column('campaign_notes',sa.String(600),nullable=False),
        sa.Column('revision',sa.Integer(),nullable=False),sa.Column('active',sa.Boolean(),nullable=False),
        sa.Column('ready',sa.Boolean(),nullable=False),sa.Column('deleted',sa.Boolean(),nullable=False),
        sa.Column('approved_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('owner_id','request_key',name='uq_gallery_owner_request'))
    op.create_index('ix_gallery_assets_owner_id','gallery_assets',['owner_id'])
    op.create_index('ix_gallery_assets_deleted','gallery_assets',['deleted'])

def downgrade():
    op.drop_table('gallery_assets')
