"""
DESTRUCTIVE - drops every table in the database so we can rebuild the
schema fresh with the changes we're about to make (surrogate key on
doctor_patient, renamed predictions column, etc).

This deletes ALL data currently in Postgres: every account, profile,
prediction, and request. Only run this because you confirmed the
current data is just test data you don't need to keep.

CASCADE handles the foreign key dependencies between tables, so the
drop order doesn't matter - Postgres will drop dependent objects too.

Run once with the venv active and Postgres (Docker) running:
    python wipe_database.py

After this, the tables won't exist at all. Don't run create_tables.py
yet - wait until the model files are updated with the new schema
changes first, then run it to recreate everything fresh.
"""

from sqlalchemy import text
from app.database import engine

TABLES = [
    "profile_change_requests",
    "reassignment_requests",
    "predictions",
    "doctor_patient",
    "doctor_profiles",
    "patient_profiles",
    "accounts",
]

with engine.connect() as conn:
    for table in TABLES:
        print(f"Dropping table: {table}")
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
    conn.commit()

print("All tables dropped. Database is now empty.")
