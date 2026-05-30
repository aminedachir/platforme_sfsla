"""
config/settings.py
------------------
Configuration classes for PSFSLA.
Load environment variables via python-dotenv.
"""

import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Base configuration shared by all environments."""

    # ── Security ──────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

    # ── Database ──────────────────────────────────────────────
    # Neon PostgreSQL via DATABASE_URL (with SSL required for Neon)
    _raw_db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'psfsla.db')}")

    # dj-database-url normalises postgresql:// → postgresql+psycopg:// (required by SQLAlchemy 2.x)
    if _raw_db_url.startswith("postgresql://"):
        _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    SQLALCHEMY_DATABASE_URI = _raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,          # detect stale connections
        "pool_recycle": 300,            # recycle every 5 min (Neon idle timeout)
        "connect_args": (
            {"sslmode": "require"}
            if _raw_db_url.startswith("postgresql")
            else {}
        ),
    }

    # ── File uploads (local fallback – not used in production) ─
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "images", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

    # ── Cloudinary ────────────────────────────────────────────
    CLOUDINARY_URL        = os.environ.get("CLOUDINARY_URL")           # cloudinary://key:secret@cloud
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY    = os.environ.get("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

    # Default public-IDs (Cloudinary) for placeholder images
    DEFAULT_AVATAR_URL    = os.environ.get(
        "DEFAULT_AVATAR_URL",
        "https://res.cloudinary.com/psfsla/image/upload/v1/defaults/default_avatar"
    )
    DEFAULT_THUMBNAIL_URL = os.environ.get(
        "DEFAULT_THUMBNAIL_URL",
        "https://res.cloudinary.com/psfsla/image/upload/v1/defaults/course_default"
    )

    # ── Certificates ──────────────────────────────────────────
    CERT_FOLDER = os.path.join(BASE_DIR, "app", "static", "certificates")

    # ── Mail ──────────────────────────────────────────────────
    MAIL_SERVER         = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT           = int(os.environ.get("MAIL_PORT", 25))
    MAIL_USE_TLS        = os.environ.get("MAIL_USE_TLS", "False").lower() == "true"
    MAIL_USERNAME       = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD       = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@psfsla.dz")

    # ── Platform identity ─────────────────────────────────────
    PLATFORM_NAME      = "PSFSLA"
    PLATFORM_FULL_NAME = "منصة لتدريب ومتابعة تكوين أخصائي المعلومات بالجزائر"
    PLATFORM_TAGLINE   = "Plateforme de Suivi de Formation Spécialiste de l'Information en Algérie"

    # ── Pagination ────────────────────────────────────────────
    COURSES_PER_PAGE = 12
    USERS_PER_PAGE   = 20


class DevelopmentConfig(Config):
    """Development — verbose errors, SQLite by default."""
    DEBUG = True
    SQLALCHEMY_ECHO = False     # Set True to log all SQL queries


class TestingConfig(Config):
    """Testing — in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}   # override: no SSL for in-memory SQLite
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production — strict security, Neon PostgreSQL, Cloudinary."""
    DEBUG = False
    SESSION_COOKIE_SECURE    = True
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = "Lax"
    REMEMBER_COOKIE_SECURE   = True


# ── Config selector ───────────────────────────────────────────
config = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
