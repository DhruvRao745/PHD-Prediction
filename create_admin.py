"""
One-off script to create an admin account directly in the database.

Admin accounts are intentionally NOT creatable through /auth/register
(that endpoint only accepts "patient"/"doctor") - admin access should
never be exposed as a public, self-service signup option. Run this
script yourself, once, whenever you need a new admin account:

    python create_admin.py
"""

from app.database import SessionLocal
from app.models.account import Account
from app.auth.security import hash_password


def main():
    db = SessionLocal()

    username = input("Admin username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return

    existing = db.query(Account).filter(Account.username == username).first()
    if existing:
        print(f"Username '{username}' already exists (role: {existing.role}).")
        return

    # Plain input(), not getpass - this is a one-off script you run
    # yourself locally, and getpass hides typing completely (no
    # asterisks either), which is easy to mistake for being broken.
    password = input("Admin password: ")
    confirm = input("Confirm password: ")
    if not password:
        print("Password cannot be empty.")
        return
    if password != confirm:
        print("Passwords do not match.")
        return

    admin = Account(
        username=username,
        email=f"{username}@admin.local",
        password_hash=hash_password(password),
        role="admin",
    )

    db.add(admin)
    db.commit()

    print(f"Admin account '{username}' created successfully.")


if __name__ == "__main__":
    main()
