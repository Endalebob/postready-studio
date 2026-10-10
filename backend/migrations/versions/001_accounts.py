"""Initial account, session, profile and rate-limit schema."""
from alembic import op
import sqlalchemy as sa
revision = '001_accounts'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users', sa.Column('id',sa.String(36),primary_key=True),sa.Column('username',sa.String(40),nullable=False,unique=True),sa.Column('email',sa.String(254),nullable=False,unique=True),sa.Column('password_hash',sa.String(255),nullable=False))
    op.create_table('sessions',sa.Column('token_hash',sa.String(64),primary_key=True),sa.Column('owner_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('profiles',sa.Column('owner_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),primary_key=True),sa.Column('data',sa.JSON(),nullable=False),sa.Column('logo_key',sa.String(200),nullable=True))
    op.create_table('auth_attempts',sa.Column('key',sa.String(64),primary_key=True),sa.Column('count',sa.Integer(),nullable=False),sa.Column('reset_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    for name in ['auth_attempts','profiles','sessions','users']:
        op.drop_table(name)
