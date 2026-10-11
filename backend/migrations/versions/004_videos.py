"""Private durable product-video jobs."""
from alembic import op
import sqlalchemy as sa
revision='004_videos'
down_revision='003_telegram'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('videos',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('request_key',sa.String(36),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),
        sa.Column('details',sa.JSON(),nullable=False),sa.Column('assets',sa.JSON(),nullable=False),
        sa.Column('output_key',sa.String(200),nullable=True),sa.Column('error',sa.String(255),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=True),
        sa.UniqueConstraint('owner_id','request_key',name='uq_video_owner_request'))
    for field in ('owner_id','status','expires_at'):
        op.create_index('ix_videos_'+field,'videos',[field])

def downgrade():
    op.drop_table('videos')
