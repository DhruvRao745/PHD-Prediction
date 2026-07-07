from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import sys
from pathlib import Path

# Same fix main.py already needs - makes sure `import app...` works
# when Alembic is run from the project root (or anywhere else).
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.database import Base, DATABASE_URL

# Import every model so Base.metadata actually knows about all of them.
# Same reason create_tables.py imports each one by hand - a model that's
# never imported anywhere is invisible to autogenerate, and Alembic will
# think it's supposed to be dropped.
from app.models.account import Account
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.models.doctor_patient import DoctorPatient
from app.models.prediction import Prediction
from app.models.reassignment_request import ReassignmentRequest
from app.models.profile_change_request import ProfileChangeRequest
from app.models.activity_log import ActivityLog
from app.models.password_reset_token import PasswordResetToken
from app.models.backup_code import BackupCode

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Reuse the same connection string app/database.py already defines,
# instead of duplicating it by hand in alembic.ini - one source of truth,
# so the two can never quietly drift apart.
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
