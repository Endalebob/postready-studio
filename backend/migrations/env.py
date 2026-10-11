from alembic import context
from app.database import engine, Base
from app import accounts
from app import ads
from app import telegram
from app import videos
with engine().connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
