from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.models.otp_code import OTPCode
from backend.app.models.role import Role
from backend.app.models.user import User
from backend.app.core.email import send_otp_email
from backend.app.core.otp import generate_otp_code, hash_otp_code, verify_otp_code
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.schemas.auth import (
    MessageResponse,
    ResendOTPRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    VerifyOTPRequest,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

settings = get_settings()

OTP_PURPOSE_EMAIL_VERIFICATION = "email_verification"


def _issue_email_verification_otp(db: Session, user: User) -> None:
    """Invalidate any pending OTPs for this user and issue + email a fresh one."""
    db.query(OTPCode).filter(
        OTPCode.user_id == user.id,
        OTPCode.purpose == OTP_PURPOSE_EMAIL_VERIFICATION,
        OTPCode.consumed_at.is_(None),
    ).delete()

    code = generate_otp_code()

    otp = OTPCode(
        user_id=user.id,
        purpose=OTP_PURPOSE_EMAIL_VERIFICATION,
        code_hash=hash_otp_code(code),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )

    db.add(otp)
    db.commit()

    # If email delivery fails, don't leave the caller thinking it succeeded.
    send_otp_email(user.email, code)


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    payload: SignupRequest,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(User.email == payload.email)
        .first()
    )

    if existing_user and existing_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    if existing_user:
        # Unverified account retrying signup: refresh password, resend OTP.
        existing_user.password_hash = hash_password(payload.password)
        user = existing_user
    else:
        default_role = (
            db.query(Role)
            .filter(Role.name == settings.DEFAULT_USER_ROLE_NAME)
            .first()
        )

        if not default_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default user role is not configured",
            )

        user = User(
            email=payload.email,
            role_id=default_role.id,
            password_hash=hash_password(payload.password),
            is_active=False,
            email_verified=False,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    _issue_email_verification_otp(db, user)

    return SignupResponse(
        message="A verification code has been sent to your email",
        email=user.email,
    )


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(
    payload: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == payload.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified",
        )

    otp = (
        db.query(OTPCode)
        .filter(
            OTPCode.user_id == user.id,
            OTPCode.purpose == OTP_PURPOSE_EMAIL_VERIFICATION,
            OTPCode.consumed_at.is_(None),
        )
        .order_by(OTPCode.created_at.desc())
        .first()
    )

    if not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code. Please request a new one",
        )

    if otp.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one",
        )

    if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Please request a new code",
        )

    if not verify_otp_code(payload.otp, otp.code_hash):
        otp.attempt_count += 1
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect verification code",
        )

    otp.consumed_at = datetime.now(timezone.utc)
    user.email_verified = True
    user.is_active = True
    db.commit()

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role_id": str(user.role_id),
        }
    )

    return TokenResponse(access_token=access_token)


@router.post("/resend-otp", response_model=MessageResponse)
def resend_otp(
    payload: ResendOTPRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == payload.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified",
        )

    last_otp = (
        db.query(OTPCode)
        .filter(
            OTPCode.user_id == user.id,
            OTPCode.purpose == OTP_PURPOSE_EMAIL_VERIFICATION,
        )
        .order_by(OTPCode.created_at.desc())
        .first()
    )

    if last_otp:
        elapsed_seconds = (
            datetime.now(timezone.utc) - last_otp.created_at
        ).total_seconds()

        if elapsed_seconds < settings.OTP_RESEND_COOLDOWN_SECONDS:
            wait_seconds = int(
                settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed_seconds
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {wait_seconds} seconds before requesting a new code",
            )

    _issue_email_verification_otp(db, user)

    return MessageResponse(
        message="A new verification code has been sent to your email"
    )


@router.post("/login")
def login(
    email: str,
    password: str,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email before logging in",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role_id": str(user.role_id),
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
