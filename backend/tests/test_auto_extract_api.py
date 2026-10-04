"""
API tests for POST /steganography/extract/auto and regression tests for
the manual POST /steganography/extract workflow.

Runs against the PostgreSQL database configured in .env, like the other
backend tests. Each test creates throwaway users (@example.com) and
images, and removes them and their files afterwards.

    python -m unittest backend.tests.test_auto_extract_api -v
"""

from __future__ import annotations

import asyncio
import io
import json
import uuid
from pathlib import Path

import numpy as np
from fastapi import HTTPException
from starlette.datastructures import UploadFile
import unittest

from backend.app.api.v1 import steganography
from backend.app.api.v1.steganography import (
    EmbedRequest,
    ExtractRequest,
    auto_extract_payload,
    embed_payload,
    extract_payload,
)
from backend.app.config import get_settings
from backend.app.core.security import hash_password
from backend.app.database import SessionLocal
from backend.app.models.image import Image
from backend.app.models.payload import Payload
from backend.app.models.role import Role
from backend.app.models.steganography_session import SteganographySession
from backend.app.models.user import User
from backend.tests.test_auto_extract import encode, natural_cover

settings = get_settings()

MESSAGE = "API-level secret: the meeting moved to Thursday."


def _upload(data: bytes, filename: str = "downloaded.png") -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=filename)


class AutoExtractApiTest(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.role = self.db.query(Role).filter(Role.name == settings.DEFAULT_USER_ROLE_NAME).one()
        self.users: list[User] = []
        self.files: list[Path] = []

        self.user = self._create_user()
        self.cover = self._register_cover(self.user)

        stego = embed_payload(
            EmbedRequest(
                cover_image_id=self.cover.id,
                method="LSB",
                payload_text=MESSAGE,
                channel_mode="G",
                lsb_bits=2,
            ),
            self.db,
            str(self.user.id),
        )
        self.stego_id = stego["stego_image_id"]
        self.stego_path = Path(stego["output_path"])
        self.files.append(self.stego_path)

    def tearDown(self):
        self.db.rollback()
        user_ids = [user.id for user in self.users]
        sessions = self.db.query(SteganographySession).filter(SteganographySession.user_id.in_(user_ids)).all()
        payload_ids = [s.payload_id for s in sessions if s.payload_id]
        for payload in self.db.query(Payload).filter(Payload.id.in_(payload_ids)).all():
            self.files.append(Path(payload.storage_path))
        for session in sessions:
            self.db.delete(session)
        self.db.flush()
        self.db.query(Image).filter(Image.owner_id.in_(user_ids)).delete(synchronize_session=False)
        self.db.query(Payload).filter(Payload.id.in_(payload_ids)).delete(synchronize_session=False)
        self.db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()
        for path in self.files:
            path.unlink(missing_ok=True)

    # -- helpers ---------------------------------------------------------

    def _create_user(self) -> User:
        user = User(
            email=f"autoextract-{uuid.uuid4().hex[:12]}@example.com",
            role_id=self.role.id,
            password_hash=hash_password("Test-password-123"),
            is_active=True,
            email_verified=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.users.append(user)
        return user

    def _register_cover(self, owner: User) -> Image:
        data = encode(natural_cover(120, 160, seed=42))
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / f"test-autoextract-{uuid.uuid4().hex}.png"
        path.write_bytes(data)
        self.files.append(path)

        image = Image(
            owner_id=owner.id,
            original_filename="cover.png",
            storage_path=str(path).replace("\\", "/"),
            mime_type="image/png",
            file_extension=".png",
            file_size_bytes=len(data),
            width=160,
            height=120,
            channels=3,
            bit_depth=8,
            sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
            metadata_json={"image_type": "COVER", "source": "USER_UPLOAD"},
            status="ACTIVE",
        )
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        return image

    def _auto(self, user: User | None = None, *, file=None, image_id=None, stream=False):
        return asyncio.run(
            auto_extract_payload(
                file=file,
                image_id=image_id,
                run_steganalysis=False,
                stream=stream,
                db=self.db,
                current_user_id=str((user or self.user).id),
            )
        )

    def _assert_slots_free(self):
        acquired = 0
        try:
            while steganography._AUTO_EXTRACT_SLOTS.acquire(blocking=False):
                acquired += 1
        finally:
            for _ in range(acquired):
                steganography._AUTO_EXTRACT_SLOTS.release()
        self.assertEqual(acquired, max(1, settings.AUTO_EXTRACT_MAX_CONCURRENT))

    # -- manual workflow regression ----------------------------------------

    def test_manual_extract_with_recorded_and_explicit_settings(self):
        recorded = extract_payload(ExtractRequest(image_id=self.stego_id, method="AUTO"), self.db, str(self.user.id))
        self.assertEqual(recorded["payload_text"], MESSAGE)
        self.assertEqual(recorded["method_source"], "RECORDED")
        self.assertEqual((recorded["channel_mode"], recorded["lsb_bits"]), ("G", 2))

        explicit = extract_payload(
            ExtractRequest(image_id=self.stego_id, method="LSB", channel_mode="G", lsb_bits=2),
            self.db,
            str(self.user.id),
        )
        self.assertEqual(explicit["payload_text"], MESSAGE)
        self.assertTrue(explicit["is_probably_text"])

    def test_manual_auto_without_record_still_asks_for_a_method(self):
        with self.assertRaises(HTTPException) as raised:
            extract_payload(ExtractRequest(image_id=self.cover.id, method="AUTO"), self.db, str(self.user.id))
        self.assertEqual(raised.exception.status_code, 400)

    # -- automatic extraction ------------------------------------------------

    def test_registered_stego_image_is_verified_by_record(self):
        result = self._auto(image_id=self.stego_id)

        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["record"]["source"], "IMAGE_RECORD")
        self.assertEqual(result["best_candidate"]["payload"]["text"], MESSAGE)
        self.assertEqual(result["image_id"], self.stego_id)
        self._assert_slots_free()

    def test_uploaded_identical_file_matches_record_by_hash(self):
        result = self._auto(file=_upload(self.stego_path.read_bytes()))

        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["record"]["source"], "HASH_MATCH")
        self.assertIsNone(result["image_id"])

    def test_other_account_gets_blind_search_not_the_record(self):
        stranger = self._create_user()

        result = self._auto(stranger, file=_upload(self.stego_path.read_bytes()))

        self.assertFalse(result["record"]["found"])
        self.assertEqual(result["status"], "PLAUSIBLE")
        best = result["best_candidate"]
        self.assertEqual(best["payload"]["text"], MESSAGE)
        self.assertEqual((best["parameters"]["channel_mode"], best["parameters"]["lsb_bits"]), ("G", 2))

    def test_other_users_image_id_is_not_found(self):
        stranger = self._create_user()
        with self.assertRaises(HTTPException) as raised:
            self._auto(stranger, image_id=self.stego_id)
        self.assertEqual(raised.exception.status_code, 404)

    def test_clean_upload_reports_not_found_with_guidance(self):
        result = self._auto(file=_upload(encode(natural_cover(seed=99))))

        self.assertEqual(result["status"], "NOT_FOUND")
        self.assertTrue(result["guidance"])
        self.assertTrue(result["methods_tested"])
        serialised = json.dumps(result, default=str)
        self.assertNotIn(str(Path.cwd()), serialised)
        self.assertNotIn("Traceback", serialised)

    def test_streamed_progress_ends_with_the_result(self):
        response = self._auto(image_id=self.stego_id, stream=True)
        self.assertEqual(response.media_type, "application/x-ndjson")

        async def read_all():
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk if isinstance(chunk, str) else chunk.decode())
            return "".join(chunks)

        events = [json.loads(line) for line in asyncio.run(read_all()).splitlines() if line]

        stages = [e["stage"] for e in events if e["type"] == "stage" and e["status"] != "running"]
        self.assertEqual(stages[0], "validate")
        self.assertIn("search", stages)
        self.assertEqual(events[-1]["type"], "result")
        self.assertEqual(events[-1]["result"]["status"], "VERIFIED")
        self._assert_slots_free()

    def test_request_validation_errors(self):
        cases = [
            ({}, 400),
            ({"file": _upload(b"x"), "image_id": self.stego_id}, 400),
            ({"file": _upload(b"plain text, not an image", "notes.png")}, 400),
            ({"file": _upload(encode(natural_cover(), "GIF"), "anim.gif")}, 400),
        ]
        for kwargs, expected in cases:
            with self.subTest(kwargs=list(kwargs)):
                with self.assertRaises(HTTPException) as raised:
                    self._auto(**kwargs)
                self.assertEqual(raised.exception.status_code, expected)
        self._assert_slots_free()

    def test_oversized_upload_is_rejected(self):
        original = steganography.settings.AUTO_EXTRACT_MAX_FILE_BYTES
        steganography.settings.AUTO_EXTRACT_MAX_FILE_BYTES = 1024
        try:
            with self.assertRaises(HTTPException) as raised:
                self._auto(file=_upload(encode(natural_cover())))
        finally:
            steganography.settings.AUTO_EXTRACT_MAX_FILE_BYTES = original
        self.assertEqual(raised.exception.status_code, 413)

    def test_busy_server_returns_429_and_frees_slots(self):
        slots = max(1, settings.AUTO_EXTRACT_MAX_CONCURRENT)
        for _ in range(slots):
            steganography._AUTO_EXTRACT_SLOTS.acquire()
        try:
            with self.assertRaises(HTTPException) as raised:
                self._auto(image_id=self.stego_id)
            self.assertEqual(raised.exception.status_code, 429)
        finally:
            for _ in range(slots):
                steganography._AUTO_EXTRACT_SLOTS.release()
        self._assert_slots_free()


if __name__ == "__main__":
    unittest.main()
