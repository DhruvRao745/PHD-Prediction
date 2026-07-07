"""Sends the actual password-reset email over Gmail SMTP.

Deliberately falls back to printing the email to the backend's console
if SMTP_USER/SMTP_APP_PASSWORD aren't set in .env yet - that way the
whole forgot-password flow can be built and tested end-to-end before
anyone has to go set up a real Gmail App Password.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_APP_PASSWORD


def _send(to_email: str, subject: str, body: str):
    if not SMTP_USER or not SMTP_APP_PASSWORD:
        print("=" * 60)
        print("SMTP not configured (see .env) - printing email instead of sending:")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(body)
        print("=" * 60)
        return

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())


def send_password_reset_email(to_email: str, username: str, reset_link: str, expire_minutes: int):
    subject = "Reset your P.H.D. Prediction password"
    body = (
        f"Hi {username},\n\n"
        f"Your username on this account is: {username}\n\n"
        "We received a request to reset the password for this account. "
        f"This link is valid for {expire_minutes} minutes:\n\n"
        f"{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email - "
        "your password won't change unless you click the link above and "
        "set a new one.\n"
    )
    _send(to_email, subject, body)


def send_doctor_assigned_email(to_email: str, patient_name: str, doctor_name: str, disease: str):
    subject = "A doctor has been assigned to you"
    body = (
        f"Hi {patient_name},\n\n"
        f"Dr. {doctor_name} has been assigned to you for {disease} on P.H.D. Prediction. "
        "They'll be able to see your prediction history and results for this condition.\n\n"
        "Log in to your account if you'd like to see more details.\n"
    )
    _send(to_email, subject, body)


def send_request_resolved_email(
    to_email: str, name: str, request_description: str, status: str, admin_note: str | None
):
    subject = f"Your request was {status}"
    note_line = f"\nAdmin's note: {admin_note}\n" if admin_note else ""
    body = (
        f"Hi {name},\n\n"
        f"Your request - {request_description} - has been {status}.\n"
        f"{note_line}\n"
        "Log in to your account for more details.\n"
    )
    _send(to_email, subject, body)


def send_high_risk_alert_email(to_email: str, patient_name: str, disease: str, confidence: float):
    subject = f"Your recent {disease} prediction came back High Risk"
    body = (
        f"Hi {patient_name},\n\n"
        f"Your most recent {disease} prediction on P.H.D. Prediction came back as "
        f"High Risk ({confidence * 100:.1f}% confidence).\n\n"
        "This is not a medical diagnosis - it's a screening estimate. Please "
        "consider discussing this result with your assigned doctor or another "
        "healthcare professional.\n\n"
        "Log in to your account to see the full result and explanation.\n"
    )
    _send(to_email, subject, body)
