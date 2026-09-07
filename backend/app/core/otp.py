import secrets

from backend.app.config import get_settings
from backend.app.core.security import hash_password, verify_password

settings = get_settings()

_DIGITS = "0123456789"


def generate_otp_code(length: int | None = None) -> str:
    """Generate a cryptographically secure numeric OTP code."""
    code_length = length or settings.OTP_LENGTH
    return "".join(secrets.choice(_DIGITS) for _ in range(code_length))


def hash_otp_code(code: str) -> str:
    """Hash an OTP code before persisting it (never store plaintext)."""
    return hash_password(code)


def verify_otp_code(code: str, code_hash: str) -> bool:
    """Check a plaintext OTP code against its stored hash."""
    return verify_password(code, code_hash)
