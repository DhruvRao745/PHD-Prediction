"""
One-off migration: adds the `admin_note` column to the
`reassignment_requests` table (already existed before this change) so
admin can leave a reason when approving/denying a request - patients
were previously left with just "denied" and no explanation.

Also covers `profile_change_requests` with IF NOT EXISTS, in case
create_tables.py was already run for that table before this column was
added to the model.

This project doesn't use Alembic - create_tables.py only creates tables
that don't exist yet, it won't add a column to an existing table. This
script runs plain ALTER TABLE statements instead, using
"IF NOT EXISTS" so it's safe to run more than once and won't touch any
existing data/rows.

Run once with the venv active and Postgres (Docker) running:
    python migrate_add_admin_note.py
"""

from sqlalchemy import text
from app.database import engine

STATEMENTS = [
    "ALTER TABLE reassignment_requests ADD COLUMN IF NOT EXISTS admin_note VARCHAR;",
    "ALTER TABLE profile_change_requests ADD COLUMN IF NOT EXISTS admin_note VARCHAR;",
]

with engine.connect() as conn:
    for statement in STATEMENTS:
        print(f"Running: {statement}")
        conn.execute(text(statement))
    conn.commit()

print("Migration complete - admin_note added to reassignment_requests and profile_change_requests.")
