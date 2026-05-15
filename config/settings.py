"""
config/settings.py
------------------
Configuration classes for PSFSLA.
Load environment variables via python-dotenv.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Base configuration shared by all environments."""

    # ── Security ──────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

    # ── Database ──────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'psfsla.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── File uploads ──────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "images", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

    # ── Mail ──────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 25))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "False").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@psfsla.dz")

    # ── Platform identity ─────────────────────────────────────
    PLATFORM_NAME = "PSFSLA"
    PLATFORM_FULL_NAME = "منصة لتدريب ومتابعة تكوين أخصائي المعلومات بالجزائر"
    PLATFORM_TAGLINE = "Plateforme de Suivi de Formation Spécialiste de l'Information en Algérie"

    # ── Pagination ────────────────────────────────────────────
    COURSES_PER_PAGE = 12
    USERS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """Development — verbose errors, SQLite."""
    DEBUG = True
    SQLALCHEMY_ECHO = False          # Set True to log all SQL queries


class TestingConfig(Config):
    """Testing — in-memory database."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production — strict security, PostgreSQL."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True


# ── Config selector ───────────────────────────────────────────
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
