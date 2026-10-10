"""Owned advertisements, fixed expiry and immutable exported revisions."""
from alembic import op
import sqlalchemy as sa
revision = '002_ads'
down_revision = '001_accounts'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('ads', sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),sa.Column('payload',sa.JSON(),nullable=False),sa.Column('sources',sa.JSON(),nullable=False),sa.Column('pending_sources',sa.JSON(),nullable=True),sa.Column('deleted',sa.Boolean(),nullable=False))
    op.create_index('ix_ads_owner_id','ads',['owner_id'])
    op.create_index('ix_ads_expires_at','ads',['expires_at'])
    op.create_table('ad_revisions',sa.Column('ad_id',sa.String(36),sa.ForeignKey('ads.id',ondelete='CASCADE'),primary_key=True),sa.Column('revision',sa.Integer(),primary_key=True),sa.Column('payload',sa.JSON(),nullable=False),sa.Column('png_key',sa.String(200),nullable=False))

def downgrade():
    op.drop_table('ad_revisions')
    op.drop_table('ads')
