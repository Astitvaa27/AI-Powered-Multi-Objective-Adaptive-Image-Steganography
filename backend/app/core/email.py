import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def _build_otp_message(to_email: str, otp_code: str) -> MIMEMultipart:
    subject = f"Your {settings.APP_NAME} verification code"

    body = (
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
        "If you did not request this, you can safely ignore this email."
    )

    message = MIMEMultipart()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    return message


def send_otp_email(to_email: str, otp_code: str) -> None:
    """Send an OTP verification code to the given email address over SMTP."""
    message = _build_otp_message(to_email, otp_code)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()

            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            server.sendmail(
                settings.SMTP_FROM_EMAIL,
                [to_email],
                message.as_string(),
            )
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", to_email, exc)
        raise
