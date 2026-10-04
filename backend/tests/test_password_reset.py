"""
Password reset and auth regression tests.

Runs against the PostgreSQL database configured in .env (the Alembic head
must be applied). Every test creates its own throwaway users with an
@example.com address and deletes them afterwards. SMTP is mocked: no
email is sent.

    python -m unittest backend.tests.test_password_reset -v
"""

import logging
import re
import threading
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from email import message_from_string
from unittest import mock

from fastapi import BackgroundTasks, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from starlette.requests import Request

from backend.app.api.v1 import auth
from backend.app.config import get_settings
from backend.app.core import email as email_module
from backend.app.core.password_reset import (
    forgot_password_ip_limiter,
    hash_reset_token,
)
from backend.app.core.security import (
    create_access_token,
    get_current_user_id,
    hash_password,
)
from backend.app.database import SessionLocal
from backend.app.models.otp_code import OTPCode
from backend.app.models.password_reset_token import PasswordResetToken
from backend.app.models.role import Role
from backend.app.models.user import User
from backend.app.schemas.auth import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ResetTokenRequest,
    SignupRequest,
    VerifyOTPRequest,
)

settings = get_settings()

TEST_DOMAIN = "example.com"
OLD_PASSWORD = "Old-password-123"
NEW_PASSWORD = "New-password-456"


class _LogCollector(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def _request(ip: str = "203.0.113.10") -> Request:
    return Request({"type": "http", "client": (ip, 50000), "headers": []})


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        forgot_password_ip_limiter.reset()

        self.db = SessionLocal()
        self.created_emails: list[str] = []

        self.role = (
            self.db.query(Role)
            .filter(Role.name == settings.DEFAULT_USER_ROLE_NAME)
            .one()
        )

        self.user = self._create_user()

        self.sent_messages: list[str] = []
        smtp_patch = mock.patch.object(email_module.smtplib, "SMTP")
        smtp_class = smtp_patch.start()
        self.addCleanup(smtp_patch.stop)

        server = smtp_class.return_value.__enter__.return_value
        server.sendmail.side_effect = (
            lambda sender, recipients, raw: self.sent_messages.append(raw)
        )
        self.smtp_server = server

        self.logs = _LogCollector()
        logging.getLogger().addHandler(self.logs)
        self.addCleanup(logging.getLogger().removeHandler, self.logs)

    def tearDown(self):
        self.db.rollback()
        cleanup = SessionLocal()
        try:
            cleanup.query(User).filter(
                User.email.in_(self.created_emails)
            ).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()
            self.db.close()

    # -- helpers ---------------------------------------------------------

    def _create_user(self, verified: bool = True) -> User:
        email = f"pwreset-{uuid.uuid4().hex[:12]}@{TEST_DOMAIN}"
        self.created_emails.append(email)

        user = User(
            email=email,
            role_id=self.role.id,
            password_hash=hash_password(OLD_PASSWORD),
            is_active=verified,
            email_verified=verified,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _forgot(self, email: str, ip: str = "203.0.113.10"):
        tasks = BackgroundTasks()
        response = auth.forgot_password(
            ForgotPasswordRequest(email=email),
            _request(ip),
            tasks,
            self.db,
        )
        # Run what FastAPI would run after sending the response.
        for task in tasks.tasks:
            task.func(*task.args, **task.kwargs)
        return response, tasks

    def _request_token(self) -> str:
        before = len(self.sent_messages)
        self._forgot(self.user.email)
        self.assertEqual(len(self.sent_messages), before + 1)
        return self._token_from_email(self.sent_messages[-1])

    @staticmethod
    def _email_parts(raw: str) -> dict[str, str]:
        parsed = message_from_string(raw)
        return {
            part.get_content_type(): part.get_payload(decode=True).decode("utf-8")
            for part in parsed.walk()
            if not part.is_multipart()
        }

    def _token_from_email(self, raw: str) -> str:
        text = self._email_parts(raw)["text/plain"]
        match = re.search(r"/reset-password#token=([A-Za-z0-9_\-]+)", text)
        self.assertIsNotNone(match, "reset link missing from email")
        return match.group(1)

    def _reset(self, token: str, password: str = NEW_PASSWORD):
        return auth.reset_password(
            ResetPasswordRequest(
                token=token,
                new_password=password,
                confirm_password=password,
            ),
            self.db,
        )

    def _assert_http_error(self, status_code: int, func, *args):
        with self.assertRaises(HTTPException) as context:
            func(*args)
        self.assertEqual(context.exception.status_code, status_code)
        return context.exception

    def _login(self, password: str) -> dict:
        return auth.login(self.user.email, password, self.db)

    # -- 1, 2: request a reset --------------------------------------------

    def test_registered_email_gets_generic_message_and_hashed_token(self):
        response, tasks = self._forgot(self.user.email)

        self.assertEqual(response.message, auth.PASSWORD_RESET_REQUESTED_MESSAGE)
        self.assertEqual(len(tasks.tasks), 1)
        self.assertEqual(len(self.sent_messages), 1)

        token = self._token_from_email(self.sent_messages[0])
        rows = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == self.user.id)
            .all()
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].token_hash, hash_reset_token(token))
        self.assertNotEqual(rows[0].token_hash, token)
        self.assertEqual(len(rows[0].token_hash), 64)

        expires_in = rows[0].expires_at - datetime.now(timezone.utc)
        self.assertLessEqual(
            expires_in,
            timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        )
        self.assertGreater(expires_in, timedelta(minutes=1))

    def test_unregistered_email_gets_identical_response_and_no_email(self):
        registered, _ = self._forgot(self.user.email)
        unknown, tasks = self._forgot(f"nobody-{uuid.uuid4().hex}@{TEST_DOMAIN}")

        self.assertEqual(unknown.model_dump(), registered.model_dump())
        self.assertEqual(tasks.tasks, [])
        self.assertEqual(len(self.sent_messages), 1)

    def test_unverified_account_gets_generic_response_and_no_email(self):
        unverified = self._create_user(verified=False)
        response, tasks = self._forgot(unverified.email)

        self.assertEqual(response.message, auth.PASSWORD_RESET_REQUESTED_MESSAGE)
        self.assertEqual(tasks.tasks, [])

    # -- 3: email content ---------------------------------------------------

    def test_email_has_html_and_text_parts_with_link_and_expiry(self):
        token = self._request_token()
        parts = self._email_parts(self.sent_messages[0])

        self.assertIn("text/plain", parts)
        self.assertIn("text/html", parts)
        for body in parts.values():
            self.assertIn(f"#token={token}", body)
            self.assertIn(
                f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes",
                body,
            )
            self.assertIn("did not request", body)
        self.assertIn("Reset password", parts["text/html"])

        recipients = self.smtp_server.sendmail.call_args.args[1]
        self.assertEqual(recipients, [self.user.email])

    # -- 4, 5: successful reset ----------------------------------------------

    def test_reset_changes_password_old_password_fails(self):
        token = self._request_token()

        status = auth.validate_reset_token(ResetTokenRequest(token=token), self.db)
        self.assertEqual(status.message, "Reset link is valid")

        self._reset(token)

        self.assertIn("access_token", self._login(NEW_PASSWORD))
        self._assert_http_error(401, self._login, OLD_PASSWORD)

    def test_reset_invalidates_existing_access_tokens(self):
        old_token = self._login(OLD_PASSWORD)["access_token"]
        self.assertEqual(
            get_current_user_id(_credentials(old_token), self.db),
            str(self.user.id),
        )

        self._reset(self._request_token())

        self._assert_http_error(
            401, get_current_user_id, _credentials(old_token), self.db
        )

        new_token = self._login(NEW_PASSWORD)["access_token"]
        self.assertEqual(
            get_current_user_id(_credentials(new_token), self.db),
            str(self.user.id),
        )

    def test_legacy_token_without_version_claim_until_reset(self):
        legacy = create_access_token(
            {"sub": str(self.user.id), "role_id": str(self.user.role_id)}
        )
        self.assertEqual(
            get_current_user_id(_credentials(legacy), self.db),
            str(self.user.id),
        )

        self._reset(self._request_token())

        self._assert_http_error(
            401, get_current_user_id, _credentials(legacy), self.db
        )

    # -- 6, 7, 8: token rejection --------------------------------------------

    def test_invalid_token_is_rejected(self):
        bogus = "x" * 43
        error = self._assert_http_error(
            400,
            auth.validate_reset_token,
            ResetTokenRequest(token=bogus),
            self.db,
        )
        self.assertEqual(error.detail, auth.INVALID_RESET_TOKEN_DETAIL)
        self._assert_http_error(400, self._reset, bogus)

    def test_expired_token_is_rejected(self):
        token = self._request_token()

        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == hash_reset_token(token)
        ).update(
            {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}
        )
        self.db.commit()

        self._assert_http_error(
            400,
            auth.validate_reset_token,
            ResetTokenRequest(token=token),
            self.db,
        )
        self._assert_http_error(400, self._reset, token)
        self.assertIn("access_token", self._login(OLD_PASSWORD))

    def test_token_cannot_be_reused(self):
        token = self._request_token()
        self._reset(token)

        self._assert_http_error(400, self._reset, token, "Another-pass-789")
        self.assertIn("access_token", self._login(NEW_PASSWORD))

    def test_newer_request_revokes_older_token(self):
        first = self._request_token()

        # Step past the cooldown instead of sleeping.
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == self.user.id
        ).update(
            {"created_at": datetime.now(timezone.utc) - timedelta(minutes=5)}
        )
        self.db.commit()

        second = self._request_token()

        self._assert_http_error(400, self._reset, first)
        self._reset(second)

    def test_concurrent_resets_with_same_token_succeed_once(self):
        token = self._request_token()
        barrier = threading.Barrier(2)
        outcomes: list[str] = []

        def attempt(password: str):
            session = SessionLocal()
            try:
                request = ResetPasswordRequest(
                    token=token,
                    new_password=password,
                    confirm_password=password,
                )
                barrier.wait()
                auth.reset_password(request, session)
                outcomes.append("ok")
            except HTTPException as exc:
                outcomes.append(str(exc.status_code))
            finally:
                session.close()

        threads = [
            threading.Thread(target=attempt, args=(f"Racing-pass-{i}xx",))
            for i in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(sorted(outcomes), ["400", "ok"])

        self.db.expire_all()
        self.assertEqual(
            self.db.get(User, self.user.id).token_version,
            1,
        )

    # -- 9: password validation ---------------------------------------------

    def test_mismatched_and_invalid_passwords_are_rejected(self):
        cases = [
            ("Mismatch-pass-1", "Mismatch-pass-2", "Passwords do not match"),
            ("short", "short", "at least 8 characters"),
            ("a" * 73, "a" * 73, "at most 72 bytes"),
            ("        ", "        ", "only whitespace"),
        ]

        for new_password, confirm_password, message in cases:
            with self.subTest(message=message):
                with self.assertRaises(ValidationError) as context:
                    ResetPasswordRequest(
                        token="t" * 43,
                        new_password=new_password,
                        confirm_password=confirm_password,
                    )
                self.assertIn(message, str(context.exception))

    def test_rejected_password_does_not_consume_token(self):
        token = self._request_token()

        with self.assertRaises(ValidationError):
            ResetPasswordRequest(
                token=token,
                new_password="short",
                confirm_password="short",
            )

        self._reset(token)

    # -- rate limiting ------------------------------------------------------

    def test_account_cooldown_suppresses_repeat_emails(self):
        self._forgot(self.user.email)
        response, tasks = self._forgot(self.user.email)

        self.assertEqual(response.message, auth.PASSWORD_RESET_REQUESTED_MESSAGE)
        self.assertEqual(tasks.tasks, [])
        self.assertEqual(len(self.sent_messages), 1)

    def test_ip_rate_limit_returns_429(self):
        ip = "198.51.100.77"
        unknown = f"nobody@{TEST_DOMAIN}"

        for _ in range(settings.PASSWORD_RESET_IP_MAX_REQUESTS):
            self._forgot(unknown, ip=ip)

        self._assert_http_error(429, self._forgot, unknown, ip)
        # Other clients are unaffected.
        self._forgot(unknown, ip="198.51.100.78")

    # -- logging / failure handling -----------------------------------------

    def test_smtp_failure_is_silent_to_client_and_not_logged_with_token(self):
        self.smtp_server.sendmail.side_effect = OSError("smtp down")

        response, _ = self._forgot(self.user.email)
        self.assertEqual(response.message, auth.PASSWORD_RESET_REQUESTED_MESSAGE)

        row = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == self.user.id)
            .one()
        )
        self.assertTrue(
            any("Failed to send password reset email" in m for m in self.logs.messages)
        )
        for message in self.logs.messages:
            self.assertNotIn("#token=", message)
            self.assertNotIn(row.token_hash, message)

    def test_full_flow_never_logs_token_or_password(self):
        token = self._request_token()
        self._reset(token)

        for message in self.logs.messages:
            self.assertNotIn(token, message)
            self.assertNotIn(NEW_PASSWORD, message)


class ExistingAuthRegressionTests(unittest.TestCase):
    """Signup -> OTP verification -> login -> protected endpoint still works."""

    def setUp(self):
        self.db = SessionLocal()
        self.email = f"signup-{uuid.uuid4().hex[:12]}@{TEST_DOMAIN}"
        self.otp_codes: list[str] = []

        otp_patch = mock.patch.object(
            auth,
            "send_otp_email",
            side_effect=lambda to, code: self.otp_codes.append(code),
        )
        otp_patch.start()
        self.addCleanup(otp_patch.stop)

    def tearDown(self):
        self.db.rollback()
        self.db.query(User).filter(User.email == self.email).delete(
            synchronize_session=False
        )
        self.db.commit()
        self.db.close()

    def test_signup_verify_login_and_protected_endpoint(self):
        auth.signup(SignupRequest(email=self.email, password=OLD_PASSWORD), self.db)
        self.assertEqual(len(self.otp_codes), 1)

        otp = self.db.query(OTPCode).join(User).filter(User.email == self.email).one()
        self.assertNotEqual(otp.code_hash, self.otp_codes[0])

        with self.assertRaises(HTTPException) as context:
            auth.login(self.email, OLD_PASSWORD, self.db)
        self.assertEqual(context.exception.status_code, 403)

        with self.assertRaises(HTTPException) as context:
            auth.resend_otp(auth.ResendOTPRequest(email=self.email), self.db)
        self.assertEqual(context.exception.status_code, 429)

        verified = auth.verify_otp(
            VerifyOTPRequest(email=self.email, otp=self.otp_codes[0]),
            self.db,
        )
        user = self.db.query(User).filter(User.email == self.email).one()
        self.assertEqual(
            get_current_user_id(_credentials(verified.access_token), self.db),
            str(user.id),
        )

        token = auth.login(self.email, OLD_PASSWORD, self.db)["access_token"]
        self.assertEqual(
            get_current_user_id(_credentials(token), self.db),
            str(user.id),
        )

        with self.assertRaises(HTTPException) as context:
            auth.login(self.email, "wrong-password", self.db)
        self.assertEqual(context.exception.status_code, 401)

    def test_garbage_bearer_token_is_rejected(self):
        for token in ["not-a-jwt", create_access_token({"sub": "not-a-uuid"})]:
            with self.assertRaises(HTTPException) as context:
                get_current_user_id(_credentials(token), self.db)
            self.assertEqual(context.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
