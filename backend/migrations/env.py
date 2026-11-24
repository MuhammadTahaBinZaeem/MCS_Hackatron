from alembic import context
from app.config import Settings
from app.database import create_database
from app.schema import metadata

config = context.config
target_metadata = metadata

if context.is_offline_mode():
    path = Settings().runtime_dir / "reportfix.db"
    context.configure(url=f"sqlite:///{path.as_posix()}", target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_database(Settings().runtime_dir)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
