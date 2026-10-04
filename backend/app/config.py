from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    APP_NAME: str = "Major Project"
    APP_ENV: str = "development"
    DEBUG: bool = True
    STORAGE_DIR: str = "storage"
    UPLOAD_DIR: str = "storage/uploads"
    STEGO_DIR: str = "storage/stego"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Origins allowed to call the API from a browser.
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ]

    # SMTP settings used for signup OTP emails.
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Major Project"
    SMTP_USE_TLS: bool = True

    # OTP settings.
    OTP_LENGTH: int = 6
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    DEFAULT_USER_ROLE_NAME: str = "user"

    # Password reset.
    # Public base URL of the frontend, used to build the emailed reset link
    # (e.g. https://app.example.com). Must be set outside development; in
    # development it falls back to the first entry of CORS_ORIGINS.
    FRONTEND_BASE_URL: str = ""
    FRONTEND_RESET_PASSWORD_PATH: str = "/reset-password"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    # Per account: minimum gap between reset emails, and an hourly cap.
    PASSWORD_RESET_COOLDOWN_SECONDS: int = 60
    PASSWORD_RESET_MAX_PER_HOUR: int = 5
    # Per client IP (in-process): requests allowed per window.
    PASSWORD_RESET_IP_MAX_REQUESTS: int = 10
    PASSWORD_RESET_IP_WINDOW_SECONDS: int = 900

    # Adaptive multi-objective embedding.
    # Candidate grid: one LSB candidate per (channel mode, bit depth),
    # plus one DCT and one DWT candidate.
    ADAPTIVE_LSB_CHANNEL_MODES: list[str] = ["RGB"]
    ADAPTIVE_LSB_BITS: list[int] = [1, 2, 3]

    # Objective weights. They are renormalised to sum to 1, and the weight
    # of any objective that cannot be measured (e.g. steganalysis model
    # missing) is redistributed proportionally over the remaining ones.
    ADAPTIVE_WEIGHT_QUALITY: float = 0.30
    ADAPTIVE_WEIGHT_SECURITY: float = 0.30
    ADAPTIVE_WEIGHT_DISTORTION: float = 0.15
    ADAPTIVE_WEIGHT_CAPACITY: float = 0.15
    ADAPTIVE_WEIGHT_ROBUSTNESS: float = 0.10

    # Normalisation ranges that map raw metrics onto 0..1 objective scores.
    # PSNR at or below the floor scores 0, at or above the ceiling scores 1.
    ADAPTIVE_PSNR_FLOOR_DB: float = 30.0
    ADAPTIVE_PSNR_CEILING_DB: float = 70.0
    # SSIM at or below this value scores 0; SSIM of 1.0 scores 1.
    ADAPTIVE_SSIM_FLOOR: float = 0.90
    # A modification rate (fraction of samples changed) at or above this
    # value gives a distortion score of 0.
    ADAPTIVE_CHANGE_RATE_CEILING: float = 0.05
    # Robustness probe: re-encode the stego image as JPEG at this quality
    # and measure how many payload bits survive extraction.
    ADAPTIVE_ROBUSTNESS_ENABLED: bool = True
    ADAPTIVE_ROBUSTNESS_JPEG_QUALITY: int = 90
    # Candidates whose weighted score is within this distance of the best
    # are treated as tied; ties go to lower P(stego), then higher PSNR.
    ADAPTIVE_SCORE_TIE_TOLERANCE: float = 0.005

    # Automatic hidden-message detection and extraction
    # (POST /steganography/extract/auto). All limits are per request.
    AUTO_EXTRACT_MAX_FILE_BYTES: int = 25 * 1024 * 1024
    # Images above this pixel count are rejected before decoding
    # (decompression-bomb protection).
    AUTO_EXTRACT_MAX_PIXELS: int = 25_000_000
    # DCT/DWT and steganalysis are slower and memory-heavy; they are skipped
    # (and reported as skipped) above this pixel count.
    AUTO_EXTRACT_MAX_TRANSFORM_PIXELS: int = 12_000_000
    # Largest payload the search will read and return.
    AUTO_EXTRACT_MAX_PAYLOAD_BYTES: int = 1024 * 1024
    # Wall-clock budget for the search; remaining configurations are
    # reported as not tested when it runs out.
    AUTO_EXTRACT_TIME_BUDGET_SECONDS: float = 20.0
    # Simultaneous automatic extractions allowed per server process.
    AUTO_EXTRACT_MAX_CONCURRENT: int = 2
    # Run the steganalysis classifier as a supporting signal.
    AUTO_EXTRACT_STEGANALYSIS_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
