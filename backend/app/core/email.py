import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def _from_header() -> str:
    return f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"


def _deliver(to_email: str, message: MIMEMultipart) -> None:
    """Send a prepared message through the configured SMTP server."""
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


def _build_otp_message(to_email: str, otp_code: str) -> MIMEMultipart:
    subject = f"Your {settings.APP_NAME} verification code"

    body = (
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
        "If you did not request this, you can safely ignore this email."
    )

    message = MIMEMultipart()
    message["From"] = _from_header()
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    return message


def send_otp_email(to_email: str, otp_code: str) -> None:
    """Send an OTP verification code to the given email address over SMTP."""
    message = _build_otp_message(to_email, otp_code)

    try:
        _deliver(to_email, message)
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", to_email, exc)
        raise


def _build_password_reset_message(
    to_email: str,
    reset_link: str,
    expires_minutes: int,
) -> MIMEMultipart:
    app_name = settings.APP_NAME
    subject = f"Reset your {app_name} password"

    text_body = (
        f"We received a request to reset the password for your {app_name} "
        "account.\n\n"
        "Open this link to choose a new password:\n"
        f"{reset_link}\n\n"
        f"The link expires in {expires_minutes} minutes and can be used once.\n\n"
        "If you did not request a password reset, you can ignore this email. "
        "Your password will not change unless you open the link and set a new "
        "one."
    )

    safe_link = html.escape(reset_link, quote=True)
    safe_app = html.escape(app_name)

    html_body = f"""\
<!DOCTYPE html>
<html lang="en">
  <body style="margin:0;padding:0;background:#f4f5f7;font-family:Segoe UI,Helvetica,Arial,sans-serif;color:#1f2933;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border:1px solid #e4e7eb;border-radius:12px;">
            <tr>
              <td style="padding:32px 32px 8px;">
                <p style="margin:0 0 4px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#7b8794;">{safe_app}</p>
                <h1 style="margin:0;font-size:20px;line-height:1.3;color:#1f2933;">Reset your password</h1>
              </td>
            </tr>
            <tr>
              <td style="padding:12px 32px 0;font-size:14px;line-height:1.6;color:#3e4c59;">
                <p style="margin:0 0 16px;">We received a request to reset the password for your account. Click the button below to choose a new password.</p>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:8px 32px 24px;">
                <a href="{safe_link}" style="display:inline-block;padding:12px 24px;border-radius:8px;background:#2563eb;color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;">Reset password</a>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 24px;font-size:13px;line-height:1.6;color:#52606d;">
                <p style="margin:0 0 12px;">This link expires in <strong>{expires_minutes} minutes</strong> and can only be used once.</p>
                <p style="margin:0 0 12px;">If the button does not work, copy this link into your browser:</p>
                <p style="margin:0;word-break:break-all;font-size:12px;color:#2563eb;">{safe_link}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 32px 32px;border-top:1px solid #e4e7eb;font-size:12px;line-height:1.6;color:#7b8794;">
                If you did not request a password reset, you can safely ignore this email. Your password will not change unless you open the link and set a new one.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    message = MIMEMultipart("alternative")
    message["From"] = _from_header()
    message["To"] = to_email
    message["Subject"] = subject
    # Clients render the last part they support, so HTML goes last.
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    return message


def send_password_reset_email(
    to_email: str,
    reset_link: str,
    expires_minutes: int,
) -> None:
    """
    Send a password reset link. Failures are logged without the link (it
    contains the token) and re-raised to the caller.
    """
    message = _build_password_reset_message(to_email, reset_link, expires_minutes)

    try:
        _deliver(to_email, message)
    except Exception as exc:
        logger.error(
            "Failed to send password reset email: %s",
            exc.__class__.__name__,
        )
        raise
