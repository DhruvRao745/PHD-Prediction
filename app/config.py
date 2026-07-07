"""Reads deployment-specific settings (SMTP credentials, frontend URL)
from a local .env file instead of hardcoding them in source - unlike
DATABASE_URL/SECRET_KEY elsewhere in this project, an email app password
genuinely can't live in a file that gets committed to git.

Copy .env.example to .env and fill in the real values - .env itself is
already gitignored, so it never gets pushed.
"""
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")

# Where the frontend actually runs - used to build the link inside the
# reset email (e.g. http://localhost:5173/reset-password?token=...).
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# How long a reset link stays valid before it's useless.
RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "30"))

# Brute-force protection: after this many wrong passwords in a row, the
# account is locked for LOCKOUT_MINUTES before another attempt is allowed.
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))
