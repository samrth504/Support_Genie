"""Alembic environment: connects with the app's own settings and models."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401 - registers every table on Base.metadata
from app.core.config import get_settings
from app.core.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# '%' must be escaped for configparser (passwords can contain it)
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata

# Tables created by LangChain (PGVector) and LangGraph (checkpointer) are managed by those
# libraries, not by us -> tell autogenerate to leave them alone.
EXTERNAL_TABLE_PREFIXES = ("langchain_pg_", "checkpoint")


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and reflected and name.startswith(EXTERNAL_TABLE_PREFIXES):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
