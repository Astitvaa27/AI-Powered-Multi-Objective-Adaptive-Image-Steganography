# StegoLab

**AI-Powered Multi-Objective Adaptive Image Steganography and Steganalysis Framework**

StegoLab is a full-stack research platform for hiding messages in images, recovering them, and detecting whether an image carries hidden data. Instead of asking the user to pick an embedding method, it embeds the message with every viable method, measures each result against five objectives, and keeps the best one, with the full comparison stored so the choice can be inspected afterwards.

| Layer | Stack |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Backend | FastAPI, SQLAlchemy 2, Pydantic, Alembic |
| Database | PostgreSQL 17 |
| Imaging and ML | NumPy, Pillow, OpenCV, PyWavelets, scikit-image, scikit-learn |

---

## What it does

**Hide a message.** Upload a cover image and a text message. In *Automatic* mode StegoLab evaluates a grid of candidates (LSB at 1, 2 and 3 bits per value, DCT, and DWT) and selects the best. In *Manual* mode you choose the method and parameters yourself. The result page shows a before/after slider, a changed-pixel map, quality measurements, and the candidate comparison.

**Extract a message.** Images hidden with StegoLab are extracted using the settings recorded for them. For unknown images, an automatic pipeline searches the supported formats within fixed time and memory limits and reports what it found, what it tried, and what it skipped.

**Analyze an image.** A Random Forest classifier estimates the probability that an image contains LSB-embedded data, and local LSB statistics highlight the regions that look most unusual. Every analysis is saved as a report.

---

## How the adaptive selection works

Each candidate is embedded, then extracted again. A candidate that does not return the exact payload is rejected. Every remaining candidate receives five objective scores in the range 0 to 1, where 1 is always better:

| Objective | Measured from | Default weight |
|---|---|---|
| Quality | PSNR and SSIM against the cover image | 0.30 |
| Security | `1 - P(stego)` from the steganalysis classifier | 0.30 |
| Distortion | Fraction of samples modified | 0.15 |
| Capacity | Headroom left after the payload | 0.15 |
| Robustness | Payload bits that survive a JPEG re-encode at quality 90 | 0.10 |

The final score is the weighted sum of the objectives. Weights can be overridden per request and are renormalised over the objectives that could actually be measured, so a missing classifier does not distort the ranking. Near-ties are broken by lower detection probability, then higher PSNR. A Pareto-optimality flag is reported for every candidate.

Objective scores use fixed reference ranges (for example PSNR between 30 dB and 70 dB) rather than min-max scaling across candidates, so a negligible difference between two candidates is not stretched into a 0-versus-1 gap. All ranges and weights are settings in `backend/app/config.py`.

This is an exhaustive search over a small discrete grid scored with a weighted sum. It is not a metaheuristic or a learned optimiser.

### Embedding methods

| Method | Domain | Notes |
|---|---|---|
| LSB | Spatial | 1 to 3 bits per value; channel modes `R`, `G`, `B`, `RGB` |
| DCT | Frequency | One bit per 8x8 block, with a 32-bit length header |
| DWT | Wavelet | Quantisation-based embedding in the HH sub-band of a 1-level Haar transform |

---

## Steganalysis

The detector is a scikit-learn `RandomForestClassifier` (200 trees, balanced class weights) over 18 hand-crafted features:

- Red-channel statistics: mean, standard deviation, minimum, maximum
- LSB ones ratio per channel and globally
- Horizontal and vertical LSB transition rates and pair rates
- RS analysis: regular ratio, singular ratio, and their difference
- Sequential LSB statistics: early versus remaining LSB ratio

The trained model ships in `storage/models/steganalysis_random_forest_18.joblib`. The scripts in `scripts/` reproduce the pipeline on BOSSbase 1.01: stego generation with random payloads, feature extraction, training, ablation, feature importance, and cross-payload evaluation. The dataset itself is not included; the scripts expect it under `storage/dataset/bossbase/source/BOSSbase_1.01`.

Regions flagged in an analysis are ranked by local LSB anomaly. They are candidates for inspection, not confirmed embedding locations.

---

## Automatic extraction pipeline

`POST /steganography/extract/auto` runs these stages in order and reports each one:

1. **Validate** the upload: size, pixel count, and decoding limits (decompression-bomb protection).
2. **Records**: exact settings stored by StegoLab for that image, matched by hash.
3. **Containers**: data appended after the end of the image, and EXIF-based formats.
4. **Search**: a bounded LSB, DCT and DWT configuration search.
5. **Validate candidates**: framing, integrity and content checks.
6. **Steganalysis** as a supporting signal. It never decides the result.
7. **Result**: ranked candidates and the final report.

Besides StegoLab's own formats, the search recognises the `stegano` library's LSB and EXIF formats and generic delimiter-terminated text. Formats are implemented as adapters in `backend/app/services/auto_extract/adapters.py`; adding one does not change the pipeline.

Default limits per request: 25 MB file size, 25 megapixels, a 20 second search budget, and 2 concurrent extractions per server process.

---

## Project structure

```
backend/
  app/
    api/v1/        REST routers: auth, images, steganography, steganalysis, optimization, datasets
    core/          security (JWT, bcrypt, permissions), OTP, password reset, email
    models/        SQLAlchemy models
    schemas/       Pydantic request and response schemas
    services/      LSB / DCT / DWT embedding, adaptive selection, metrics,
                   steganalysis, auto_extract pipeline
    config.py      all settings, loaded from .env
    main.py        FastAPI application
  tests/           unit and API tests
frontend/          React + TypeScript client (see frontend/README.md)
migrations/        Alembic migrations
scripts/           BOSSbase dataset, training and evaluation scripts
storage/models/    trained steganalysis model
docker-compose.yml PostgreSQL for local development
```

---

## Getting started

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- Docker, for the local PostgreSQL instance
- An SMTP account. Sign-up is confirmed with an emailed one-time code, so the backend needs to be able to send mail.

### 1. Clone and start the database

```bash
git clone https://github.com/Astitvaa27/AI-Powered-Multi-Objective-Adaptive-Image-Steganography.git
cd AI-Powered-Multi-Objective-Adaptive-Image-Steganography
docker compose up -d
```

The credentials in `docker-compose.yml` are for local development only.

### 2. Configure the backend

Create a `.env` file in the repository root:

```env
DATABASE_URL=postgresql+psycopg://major_project:major_project_dev_password@localhost:5432/major_project
JWT_SECRET_KEY=replace-with-a-long-random-string

APP_NAME=StegoLab

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-address@example.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-address@example.com
SMTP_FROM_NAME=StegoLab
```

`DATABASE_URL` and `JWT_SECRET_KEY` are required. Every other setting has a default in `backend/app/config.py`.

### 3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install fastapi "uvicorn[standard]" pydantic-settings "pydantic[email]" \
    "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt==4.0.1" \
    numpy pillow opencv-python PyWavelets scikit-image "scikit-learn==1.9.0" joblib pandas
```

`requirements.txt` currently lists only the database packages, so the second command installs the rest. `bcrypt` is pinned because `passlib` 1.7.4 does not work with newer `bcrypt` releases, and `scikit-learn` is pinned to the version the shipped model was trained with.

### 4. Apply migrations

```bash
alembic upgrade head
```

### 5. Register the steganalysis model

The analysis endpoints look up an active model record in the database. On a fresh database, create it once by running this from the repository root in a `python` shell:

```python
import hashlib
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.database import engine
from backend.app.models.model_version import ModelVersion

path = Path("storage/models/steganalysis_random_forest_18.joblib")

with Session(engine) as db:
    db.add(ModelVersion(
        name="Steganalysis Random Forest",
        version="1.0",
        framework="scikit-learn",
        architecture="RandomForestClassifier",
        task_type="BINARY_CLASSIFICATION",
        artifact_path=str(path),
        artifact_hash=hashlib.sha256(path.read_bytes()).hexdigest(),
        status="ACTIVE",
    ))
    db.commit()
```

### 6. Run the backend

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

Interactive API documentation is served at `http://127.0.0.1:8000/docs`.

### 7. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

The app is served at `http://localhost:5173`. Set `VITE_API_BASE_URL` if the backend is not at `http://127.0.0.1:8000`. Frontend routes, scripts and structure are documented in [`frontend/README.md`](frontend/README.md).

---

## API overview

Protected routes expect a bearer token, issued by `/auth/login` or by `/auth/verify-otp` after sign-up.

| Prefix | Purpose |
|---|---|
| `/auth` | Sign-up, OTP verification and resend, login, forgot and reset password |
| `/users` | User records |
| `/images` | Upload, list, fetch metadata, download file |
| `/steganography` | Methods, capacity, manual embed, adaptive embed, extract, automatic extract, session history |
| `/steganalysis` | Analyze an upload or a stored image, model details, statistics, sessions, reports |
| `/optimization-runs` | Optimization runs with their iterations, candidate configurations and objective scores |
| `/datasets`, `/payloads` | Dataset and payload records |
| `/health`, `/health/db` | Liveness and database connectivity |

Accepted image formats: PNG, JPEG, BMP, TIFF, PGM, PPM and WebP, up to 25 MB.

---

## Tests

```bash
# Extraction pipeline: synthetic images, no database needed
python -m unittest backend.tests.test_auto_extract -v

# Auth, password reset and extraction API: need the database with migrations applied
python -m unittest backend.tests.test_password_reset backend.tests.test_auto_extract_api -v
```

The database tests create throwaway `@example.com` users and delete them afterwards. SMTP is mocked, so no email is sent.

---

## Security

- Passwords are hashed with bcrypt. Sessions use signed JWT bearer tokens that expire after 60 minutes by default.
- Sign-up requires a 6-digit emailed code that is stored hashed, expires after 10 minutes, allows 5 attempts, and has a resend cooldown.
- Password-reset tokens are stored hashed and expire after 30 minutes, with a per-account cooldown, an hourly cap, and a per-IP request limit.
- Validation errors on `/auth` routes never echo the submitted body, so passwords and reset tokens are not sent back in error responses.
- Images are scoped to the user who uploaded them, and dataset management is gated by a role and permission check.
- Uploads are restricted by extension and file size, and automatic extraction rejects oversized images before decoding them.

---

## Scope and limitations

- Messages are text only and are not encrypted before embedding.
- The adaptive selector searches a small fixed grid. It does not learn or adapt its search between runs.
- The classifier is built on LSB statistics and its training scripts generate LSB-embedded images, so treat its verdict on other embedding methods with caution.
- Embedding is a single synchronous request; very large images can take a minute or more.
- An image that is edited or re-saved after download usually loses its hidden message.

---

## Author

**Astitva Mhatre** · [GitHub](https://github.com/Astitvaa27) · [LinkedIn](https://linkedin.com/in/astitva-mhatre)

Final-year engineering major project.
