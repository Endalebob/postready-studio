"""Default-deny workspace access and approval audit trail."""
from alembic import op
import sqlalchemy as sa
revision='008_waitlist'
down_revision='007_preparations'
branch_labels=None
depends_on=None

def upgrade():
    for column in [
        sa.Column('access_status',sa.String(20),nullable=False,server_default='pending'),
        sa.Column('is_admin',sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column('image_limit',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('image_requests_used',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('access_revision',sa.Integer(),nullable=False,server_default='1'),
        sa.Column('requested_at',sa.DateTime(timezone=True),nullable=True),
    ]:
        op.add_column('users',column)
    op.execute(sa.text('UPDATE users SET requested_at=CURRENT_TIMESTAMP WHERE requested_at IS NULL'))
    op.create_table('access_audit',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('actor_id',sa.String(36),sa.ForeignKey('users.id',ondelete='SET NULL'),nullable=True),
        sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('action',sa.String(30),nullable=False),
        sa.Column('image_limit',sa.Integer(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    op.drop_table('access_audit')
    with op.batch_alter_table('users') as batch:
        for name in ['requested_at','access_revision','image_requests_used','image_limit','is_admin','access_status']:
            batch.drop_column(name)
