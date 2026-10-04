import logging
from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.models.otp_code import OTPCode
from backend.app.models.password_reset_token import PasswordResetToken
from backend.app.models.role import Role
from backend.app.models.user import User
from backend.app.core.email import send_otp_email, send_password_reset_email
from backend.app.core.otp import generate_otp_code, hash_otp_code, verify_otp_code
from backend.app.core.password_reset import (
    build_reset_link,
    forgot_password_ip_limiter,
    generate_reset_token,
    hash_reset_token,
)
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.schemas.auth import (
    ForgotPasswordRequest,
    MessageResponse,
    ResendOTPRequest,
    ResetPasswordRequest,
    ResetTokenRequest,
    ResetTokenStatusResponse,
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
logger = logging.getLogger(__name__)

OTP_PURPOSE_EMAIL_VERIFICATION = "email_verification"

# Identical for every outcome so responses never reveal whether an
# account exists for the submitted email.
PASSWORD_RESET_REQUESTED_MESSAGE = (
    "If an account exists for this email, you will receive password reset "
    "instructions."
)
INVALID_RESET_TOKEN_DETAIL = (
    "This password reset link is invalid or has expired. "
    "Please request a new one."
)


def _create_user_access_token(user: User) -> str:
    """Issue an access token bound to the user's current token version."""
    return create_access_token(
        data={
            "sub": str(user.id),
            "role_id": str(user.role_id),
            "tv": user.token_version,
        }
    )


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

    access_token = _create_user_access_token(user)

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

    access_token = _create_user_access_token(user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def _is_reset_eligible(user: User | None) -> bool:
    # Unverified accounts can simply sign up again, which already resets
    # their password, so reset links are only issued to active accounts.
    return bool(
        user
        and user.email_verified
        and user.is_active
        and user.deleted_at is None
    )


def _send_password_reset_email_safely(
    to_email: str,
    reset_link: str,
    expires_minutes: int,
) -> None:
    """Runs after the response is sent; failures are logged, not surfaced."""
    try:
        send_password_reset_email(to_email, reset_link, expires_minutes)
    except Exception:
        # Already logged (without the link) by the email module.
        pass


def _issue_password_reset(
    db: Session,
    user: User,
    background_tasks: BackgroundTasks,
) -> None:
    now = datetime.now(timezone.utc)

    recent_requests = (
        db.query(PasswordResetToken.created_at)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= now - timedelta(hours=1),
        )
        .order_by(PasswordResetToken.created_at.desc())
        .all()
    )

    # Throttled silently: an error here would reveal that the account exists.
    if recent_requests:
        elapsed = (now - recent_requests[0].created_at).total_seconds()

        if elapsed < settings.PASSWORD_RESET_COOLDOWN_SECONDS:
            return

    if len(recent_requests) >= settings.PASSWORD_RESET_MAX_PER_HOUR:
        return

    token = generate_reset_token()
    reset_link = build_reset_link(token)

    if not reset_link:
        logger.error(
            "Password reset email not sent: FRONTEND_BASE_URL is not configured."
        )
        return

    # Only the newest link is valid.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )

    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(token),
            expires_at=now
            + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        )
    )
    db.commit()

    # Sent after the response, so delivery time cannot reveal the account.
    background_tasks.add_task(
        _send_password_reset_email_safely,
        user.email,
        reset_link,
        settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"

    # Applies to every request regardless of the email, so it reveals nothing.
    if not forgot_password_ip_limiter.allow(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please try again later",
        )

    user = (
        db.query(User)
        .filter(User.email == payload.email)
        .first()
    )

    if _is_reset_eligible(user):
        _issue_password_reset(db, user, background_tasks)

    return MessageResponse(message=PASSWORD_RESET_REQUESTED_MESSAGE)


@router.post(
    "/reset-password/validate",
    response_model=ResetTokenStatusResponse,
)
def validate_reset_token(
    payload: ResetTokenRequest,
    db: Session = Depends(get_db),
):
    """Check a reset link before showing the new-password form."""
    record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == hash_reset_token(payload.token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    user = db.get(User, record.user_id) if record else None

    if not record or not _is_reset_eligible(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_RESET_TOKEN_DETAIL,
        )

    return ResetTokenStatusResponse(
        message="Reset link is valid",
        expires_at=record.expires_at,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    # Hash first so the token row is locked for as short a time as possible.
    new_password_hash = hash_password(payload.new_password)
    now = datetime.now(timezone.utc)

    # Claim the token atomically. Under concurrent requests Postgres lets
    # exactly one UPDATE match; the others see used_at already set.
    claimed_user_id = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == hash_reset_token(payload.token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(PasswordResetToken.user_id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()

    if claimed_user_id is None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_RESET_TOKEN_DETAIL,
        )

    user = (
        db.query(User)
        .filter(User.id == claimed_user_id)
        .with_for_update()
        .first()
    )

    if not _is_reset_eligible(user):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_RESET_TOKEN_DETAIL,
        )

    user.password_hash = new_password_hash
    # Invalidates every access token issued before this reset.
    user.token_version = User.token_version + 1

    # Any other outstanding links for this account stop working too.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )

    db.commit()

    logger.info("Password reset completed for user %s", user.id)

    return MessageResponse(
        message=(
            "Your password has been reset. "
            "You can now sign in with your new password"
        )
    )
