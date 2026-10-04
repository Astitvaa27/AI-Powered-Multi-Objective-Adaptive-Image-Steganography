from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class SignupResponse(BaseModel):
    message: str
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=8)


class ResendOTPRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


# bcrypt only uses the first 72 bytes of a password; longer input would be
# silently truncated, so it is rejected instead.
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72


def _check_password_policy(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise PydanticCustomError(
            "password_too_short",
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.",
        )

    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise PydanticCustomError(
            "password_too_long",
            f"Password must be at most {PASSWORD_MAX_BYTES} bytes long.",
        )

    if not password.strip():
        raise PydanticCustomError(
            "password_blank",
            "Password cannot be only whitespace.",
        )

    return password


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)


class ResetTokenStatusResponse(BaseModel):
    message: str
    expires_at: datetime


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _check_password_policy(value)

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise PydanticCustomError(
                "password_mismatch",
                "Passwords do not match.",
            )
        return self
