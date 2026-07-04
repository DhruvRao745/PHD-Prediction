"""
One-off migration: adds the `deleted_at` column to the `predictions` and
`doctor_patient` tables for soft-delete support.

This project doesn't use Alembic - create_tables.py only creates tables
that don't exist yet, it won't add a column to an existing table. This
script runs plain ALTER TABLE statements instead, using
"IF NOT EXISTS" so it's safe to run more than once and won't touch any
existing data/rows.

Run once with the venv active and Postgres (Docker) running:
    python migrate_add_soft_delete.py
"""

from sqlalchemy import text
from app.database import engine

STATEMENTS = [
    "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;",
    "ALTER TABLE doctor_patient ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;",
]

with engine.connect() as conn:
    for statement in STATEMENTS:
        print(f"Running: {statement}")
        conn.execute(text(statement))
    conn.commit()

print("Migration complete - deleted_at added to predictions and doctor_patient.")
