"""Verified channel links and durable publishing outcomes."""
from alembic import op
import sqlalchemy as sa
revision = '003_telegram'
down_revision = '002_ads'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('telegram_connections',sa.Column('owner_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),primary_key=True),
        sa.Column('connection_id',sa.String(36),nullable=False),sa.Column('active',sa.Boolean(),nullable=False),
        sa.Column('challenge_hash',sa.String(64),unique=True,nullable=True),sa.Column('challenge_expires',sa.DateTime(timezone=True),nullable=True),
        sa.Column('telegram_user_id',sa.String(32),nullable=True),sa.Column('observed_chat',sa.JSON(),nullable=True),
        sa.Column('chat_id',sa.String(32),unique=True,nullable=True),sa.Column('title',sa.String(255),nullable=True),sa.Column('username',sa.String(255),nullable=True),
        sa.Column('checked_at',sa.DateTime(timezone=True),nullable=True),sa.Column('error',sa.String(255),nullable=True))
    op.create_table('telegram_bot_state',sa.Column('key',sa.String(64),primary_key=True),sa.Column('offset',sa.Integer(),nullable=False))
    op.create_table('publish_attempts',sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('ad_id',sa.String(36),sa.ForeignKey('ads.id',ondelete='SET NULL'),nullable=True),sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('connection_id',sa.String(36),nullable=False),sa.Column('chat_id',sa.String(32),nullable=False),sa.Column('title',sa.String(255),nullable=False),
        sa.Column('username',sa.String(255),nullable=True),sa.Column('status',sa.String(20),nullable=False),sa.Column('detail',sa.String(255),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),sa.Column('message_id',sa.String(32),nullable=True),
        sa.UniqueConstraint('owner_id','ad_id','revision','connection_id',name='uq_publish_revision_destination'))
    op.create_index('ix_publish_attempts_owner_id','publish_attempts',['owner_id'])
    op.create_index('ix_publish_attempts_status','publish_attempts',['status'])

def downgrade():
    op.drop_table('publish_attempts')
    op.drop_table('telegram_bot_state')
    op.drop_table('telegram_connections')
