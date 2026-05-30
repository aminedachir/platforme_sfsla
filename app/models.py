"""
app/models.py
-------------
All SQLAlchemy models for PSFSLA.
Tables: User, Role, Category, Course, Resource, Enrollment,
        LiveSession, Certificate, Notification,
        CompletedResource, AttendedSession

Changes for Cloudinary deployment
----------------------------------
* User.avatar      – now stores full Cloudinary secure_url (or public_id)
* Course.thumbnail – now stores full Cloudinary secure_url (or public_id)
* Resource.file_path – now stores Cloudinary secure_url for uploaded files
* Certificate.file_path – stores Cloudinary secure_url for generated PDFs
  (or keeps local path when Cloudinary is not used for PDFs)

All defaults point to the placeholder images defined in config/settings.py.
"""

from datetime import datetime, timezone
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _default_avatar():
    try:
        return current_app.config.get(
            "DEFAULT_AVATAR_URL",
            "https://res.cloudinary.com/psfsla/image/upload/v1/defaults/default_avatar",
        )
    except RuntimeError:
        return "https://res.cloudinary.com/psfsla/image/upload/v1/defaults/default_avatar"


def _default_thumbnail():
    try:
        return current_app.config.get(
            "DEFAULT_THUMBNAIL_URL",
            "https://res.cloudinary.com/psfsla/image/upload/v1/defaults/course_default",
        )
    except RuntimeError:
        return "https://res.cloudinary.com/psfsla/image/upload/v1/defaults/course_default"


# ──────────────────────────────────────────────────────────────
#  Association tables (many-to-many)
# ──────────────────────────────────────────────────────────────

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"),  primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"),  primary_key=True),
)


# ──────────────────────────────────────────────────────────────
#  Role
# ──────────────────────────────────────────────────────────────

class Role(db.Model):
    __tablename__ = "roles"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(64),  unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f"<Role {self.name}>"


# ──────────────────────────────────────────────────────────────
#  User
# ──────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # Identity
    first_name  = db.Column(db.String(64),  nullable=False)
    last_name   = db.Column(db.String(64),  nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone       = db.Column(db.String(20))
    wilaya      = db.Column(db.String(64))

    # Auth
    password_hash   = db.Column(db.String(256), nullable=False)
    is_active       = db.Column(db.Boolean, default=True)
    is_approved     = db.Column(db.Boolean, default=True)
    email_confirmed = db.Column(db.Boolean, default=False)

    # Profile
    # avatar stores the Cloudinary secure_url (full https://…) or public_id.
    # String length increased to 1024 to accommodate long CDN URLs.
    avatar      = db.Column(db.String(1024), default=_default_avatar)
    bio         = db.Column(db.Text)
    speciality  = db.Column(db.String(128))
    institution = db.Column(db.String(128))

    # Timestamps
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login  = db.Column(db.DateTime)

    # Relationships
    roles          = db.relationship("Role",         secondary=user_roles,
                                     backref="users", lazy="dynamic")
    enrollments    = db.relationship("Enrollment",   backref="student",   lazy="dynamic")
    certificates   = db.relationship("Certificate",  backref="holder",    lazy="dynamic")
    notifications  = db.relationship("Notification", backref="recipient", lazy="dynamic")
    courses_taught = db.relationship("Course",       backref="professor", lazy="dynamic",
                                     foreign_keys="Course.professor_id")

    # ── Password helpers ──────────────────────────────────────
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ── Role helpers ──────────────────────────────────────────
    def has_role(self, role_name):
        return self.roles.filter_by(name=role_name).first() is not None

    @property
    def is_admin(self):
        return self.has_role("admin")

    @property
    def is_professor(self):
        return self.has_role("professor")

    @property
    def is_student(self):
        return self.has_role("student")

    # ── Display helpers ───────────────────────────────────────
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def avatar_url(self):
        """Always return a usable image URL."""
        if self.avatar and (
            self.avatar.startswith("http://") or self.avatar.startswith("https://")
        ):
            return self.avatar
        return _default_avatar()

    def __repr__(self):
        return f"<User {self.email}>"


# ──────────────────────────────────────────────────────────────
#  Category
# ──────────────────────────────────────────────────────────────

class Category(db.Model):
    __tablename__ = "categories"

    id          = db.Column(db.Integer, primary_key=True)
    name_ar     = db.Column(db.String(128), nullable=False)
    name_fr     = db.Column(db.String(128), nullable=False)
    slug        = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon        = db.Column(db.String(64),  default="bi-book")
    color       = db.Column(db.String(16),  default="#1B2A52")
    order       = db.Column(db.Integer,     default=0)

    courses = db.relationship("Course", backref="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.name_fr}>"


# ──────────────────────────────────────────────────────────────
#  Course (Formation)
# ──────────────────────────────────────────────────────────────

class Course(db.Model):
    __tablename__ = "courses"

    id             = db.Column(db.Integer, primary_key=True)
    title_ar       = db.Column(db.String(255), nullable=False)
    title_fr       = db.Column(db.String(255), nullable=False)
    description    = db.Column(db.Text)
    objectives     = db.Column(db.Text)

    # thumbnail stores the Cloudinary secure_url (full https://…) or public_id.
    thumbnail      = db.Column(db.String(1024), default=_default_thumbnail)

    # Metadata
    level          = db.Column(db.String(32),  default="debutant")
    duration_hours = db.Column(db.Integer,     default=0)
    language       = db.Column(db.String(16),  default="ar")
    is_published   = db.Column(db.Boolean,     default=False)
    is_free        = db.Column(db.Boolean,     default=True)
    price          = db.Column(db.Float,       default=0.0)

    # Foreign keys
    professor_id   = db.Column(db.Integer, db.ForeignKey("users.id"),        nullable=False)
    category_id    = db.Column(db.Integer, db.ForeignKey("categories.id"))

    # Timestamps
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at     = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    resources      = db.relationship("Resource",    backref="course", lazy="dynamic",
                                     cascade="all, delete-orphan")
    enrollments    = db.relationship("Enrollment",  backref="course", lazy="dynamic",
                                     cascade="all, delete-orphan")
    live_sessions  = db.relationship("LiveSession", backref="course", lazy="dynamic",
                                     cascade="all, delete-orphan")
    certificates   = db.relationship("Certificate", backref="course", lazy="dynamic",
                                     cascade="all, delete-orphan", passive_deletes=True)

    @property
    def enrollment_count(self):
        return self.enrollments.count()

    @property
    def thumbnail_url(self):
        """Always return a usable image URL."""
        if self.thumbnail and (
            self.thumbnail.startswith("http://") or self.thumbnail.startswith("https://")
        ):
            return self.thumbnail
        return _default_thumbnail()

    def __repr__(self):
        return f"<Course {self.title_fr}>"


# ──────────────────────────────────────────────────────────────
#  Resource (PDF, video link, etc.)
# ──────────────────────────────────────────────────────────────

class Resource(db.Model):
    __tablename__ = "resources"

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(255), nullable=False)
    type        = db.Column(db.String(32),  nullable=False)   # pdf | video | link | slide

    # file_path now stores the Cloudinary secure_url for uploaded files (pdf, slide…)
    file_path   = db.Column(db.String(1024))

    # url is used for external links (video, website…)
    url         = db.Column(db.String(1024))

    description = db.Column(db.Text)
    order       = db.Column(db.Integer, default=0)
    is_public   = db.Column(db.Boolean, default=False)

    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"),
                            nullable=False)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def access_url(self):
        """Return the effective URL (Cloudinary or external)."""
        return self.file_path or self.url or ""

    def __repr__(self):
        return f"<Resource {self.title} [{self.type}]>"


# ──────────────────────────────────────────────────────────────
#  Enrollment
# ──────────────────────────────────────────────────────────────

class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey("users.id",    ondelete="CASCADE"), nullable=False)
    course_id    = db.Column(db.Integer, db.ForeignKey("courses.id",  ondelete="CASCADE"), nullable=False)
    status       = db.Column(db.String(32), default="active")
    progress     = db.Column(db.Float,      default=0.0)
    enrolled_at  = db.Column(db.DateTime,   default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint("student_id", "course_id", name="uq_enrollment"),
    )

    def __repr__(self):
        return f"<Enrollment student={self.student_id} course={self.course_id}>"


# ──────────────────────────────────────────────────────────────
#  LiveSession
# ──────────────────────────────────────────────────────────────

class LiveSession(db.Model):
    __tablename__ = "live_sessions"

    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(255), nullable=False)
    description   = db.Column(db.Text)
    platform      = db.Column(db.String(64),  default="zoom")
    meeting_url   = db.Column(db.String(512))
    meeting_id    = db.Column(db.String(128))
    password      = db.Column(db.String(64))

    scheduled_at  = db.Column(db.DateTime, nullable=False)
    duration_min  = db.Column(db.Integer,  default=60)
    is_recorded   = db.Column(db.Boolean,  default=False)
    recording_url = db.Column(db.String(512))
    status        = db.Column(db.String(32), default="scheduled")

    course_id     = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"),
                              nullable=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<LiveSession '{self.title}' @ {self.scheduled_at}>"


# ──────────────────────────────────────────────────────────────
#  Certificate
# ──────────────────────────────────────────────────────────────

class Certificate(db.Model):
    __tablename__ = "certificates"

    id             = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.String(64),   unique=True, nullable=False)
    student_id     = db.Column(db.Integer, db.ForeignKey("users.id",   ondelete="CASCADE"), nullable=False)
    course_id      = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    issued_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # file_path stores the Cloudinary secure_url for the generated PDF certificate
    file_path      = db.Column(db.String(1024))

    is_valid       = db.Column(db.Boolean, default=True)

    user       = db.relationship("User",   foreign_keys=[student_id], lazy="joined")
    course_rel = db.relationship("Course", foreign_keys=[course_id],  lazy="joined")

    def __repr__(self):
        return f"<Certificate {self.certificate_id}>"


# ──────────────────────────────────────────────────────────────
#  Notification
# ──────────────────────────────────────────────────────────────

class Notification(db.Model):
    __tablename__ = "notifications"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title      = db.Column(db.String(255), nullable=False)
    message    = db.Column(db.Text)
    type       = db.Column(db.String(32),  default="info")
    is_read    = db.Column(db.Boolean,     default=False)
    link       = db.Column(db.String(512))
    created_at = db.Column(db.DateTime,   default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Notification for user={self.user_id}: {self.title}>"


# ──────────────────────────────────────────────────────────────
#  CompletedResource
# ──────────────────────────────────────────────────────────────

class CompletedResource(db.Model):
    __tablename__ = "completed_resources"

    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey("users.id",      ondelete="CASCADE"), nullable=False, index=True)
    resource_id  = db.Column(db.Integer, db.ForeignKey("resources.id"),  nullable=False)
    course_id    = db.Column(db.Integer, db.ForeignKey("courses.id",     ondelete="CASCADE"), nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    student  = db.relationship("User",     foreign_keys=[student_id])
    resource = db.relationship("Resource", foreign_keys=[resource_id])
    course   = db.relationship("Course",   foreign_keys=[course_id])

    __table_args__ = (
        db.UniqueConstraint("student_id", "resource_id", name="uq_completed_resource"),
    )

    def __repr__(self):
        return f"<CompletedResource student={self.student_id} resource={self.resource_id}>"


# ──────────────────────────────────────────────────────────────
#  AttendedSession
# ──────────────────────────────────────────────────────────────

class AttendedSession(db.Model):
    __tablename__ = "attended_sessions"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("users.id",         ondelete="CASCADE"), nullable=False, index=True)
    session_id  = db.Column(db.Integer, db.ForeignKey("live_sessions.id"), nullable=False)
    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id",        ondelete="CASCADE"), nullable=False, index=True)
    attended_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    student = db.relationship("User",        foreign_keys=[student_id])
    session = db.relationship("LiveSession", foreign_keys=[session_id])
    course  = db.relationship("Course",      foreign_keys=[course_id])

    __table_args__ = (
        db.UniqueConstraint("student_id", "session_id", name="uq_attended_session"),
    )

    def __repr__(self):
        return f"<AttendedSession student={self.student_id} session={self.session_id}>"
