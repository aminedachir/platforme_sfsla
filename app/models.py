"""
app/models.py
-------------
All SQLAlchemy models for PSFSLA.
Tables: User, Role, Category, Course, Resource, Enrollment,
        LiveSession, Certificate, Notification, Progress,
        CompletedResource, AttendedSession          ← جديد
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


# ──────────────────────────────────────────────────────────────
#  Association tables (many-to-many)
# ──────────────────────────────────────────────────────────────

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
)


# ──────────────────────────────────────────────────────────────
#  Role
# ──────────────────────────────────────────────────────────────

class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)   # admin | professor | student
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
    first_name = db.Column(db.String(64), nullable=False)
    last_name  = db.Column(db.String(64), nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone      = db.Column(db.String(20))
    wilaya     = db.Column(db.String(64))          # Algerian province

    # Auth
    password_hash = db.Column(db.String(256), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)
    is_approved   = db.Column(db.Boolean, default=True)  # professors need admin approval
    email_confirmed = db.Column(db.Boolean, default=False)

    # Profile
    avatar      = db.Column(db.String(256), default="default.png")
    bio         = db.Column(db.Text)
    speciality  = db.Column(db.String(128))       # for professors
    institution = db.Column(db.String(128))

    # Timestamps
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login  = db.Column(db.DateTime)

    # Relationships
    roles       = db.relationship("Role", secondary=user_roles, backref="users", lazy="dynamic")
    enrollments   = db.relationship("Enrollment",        backref="student",   lazy="dynamic",
                                     cascade="all, delete-orphan", passive_deletes=True)
    certificates  = db.relationship("Certificate",       backref="holder",    lazy="dynamic",
                                     cascade="all, delete-orphan", passive_deletes=True)
    notifications = db.relationship("Notification",      backref="recipient", lazy="dynamic",
                                     cascade="all, delete-orphan", passive_deletes=True)
    courses_taught = db.relationship("Course", backref="professor", lazy="dynamic",
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

    def __repr__(self):
        return f"<User {self.email}>"


# ──────────────────────────────────────────────────────────────
#  Category
# ──────────────────────────────────────────────────────────────

class Category(db.Model):
    __tablename__ = "categories"

    id          = db.Column(db.Integer, primary_key=True)
    name_ar     = db.Column(db.String(128), nullable=False)   # Arabic name
    name_fr     = db.Column(db.String(128), nullable=False)   # French name
    slug        = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon        = db.Column(db.String(64), default="bi-book")  # Bootstrap icon name
    color       = db.Column(db.String(16), default="#1B2A52")
    order       = db.Column(db.Integer, default=0)

    courses     = db.relationship("Course", backref="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.name_fr}>"


# ──────────────────────────────────────────────────────────────
#  Course (Formation)
# ──────────────────────────────────────────────────────────────

class Course(db.Model):
    __tablename__ = "courses"

    id            = db.Column(db.Integer, primary_key=True)
    title_ar      = db.Column(db.String(255), nullable=False)
    title_fr      = db.Column(db.String(255), nullable=False)
    description   = db.Column(db.Text)
    objectives    = db.Column(db.Text)            # JSON list of objectives
    thumbnail     = db.Column(db.String(256), default="course_default.png")

    # Metadata
    level         = db.Column(db.String(32), default="debutant")  # debutant | intermediaire | avance
    duration_hours = db.Column(db.Integer, default=0)
    language      = db.Column(db.String(16), default="ar")        # ar | fr | ar_fr
    is_published  = db.Column(db.Boolean, default=False)
    is_free       = db.Column(db.Boolean, default=True)
    price         = db.Column(db.Float, default=0.0)

    # Foreign keys
    professor_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id   = db.Column(db.Integer, db.ForeignKey("categories.id"))

    # Timestamps
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    resources     = db.relationship("Resource", backref="course", lazy="dynamic",
                                    cascade="all, delete-orphan")
    enrollments   = db.relationship("Enrollment", backref="course", lazy="dynamic",
                                    cascade="all, delete-orphan")
    live_sessions = db.relationship("LiveSession", backref="course", lazy="dynamic",
                                    cascade="all, delete-orphan")
    certificates  = db.relationship("Certificate", backref="course", lazy="dynamic")

    @property
    def enrollment_count(self):
        return self.enrollments.count()

    def __repr__(self):
        return f"<Course {self.title_fr}>"


# ──────────────────────────────────────────────────────────────
#  Resource (PDF, video link, etc.)
# ──────────────────────────────────────────────────────────────

class Resource(db.Model):
    __tablename__ = "resources"

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(255), nullable=False)
    type        = db.Column(db.String(32), nullable=False)  # pdf | video | link | slide
    file_path   = db.Column(db.String(512))                 # for uploaded files
    url         = db.Column(db.String(512))                 # for external links
    description = db.Column(db.Text)
    order       = db.Column(db.Integer, default=0)
    is_public   = db.Column(db.Boolean, default=False)      # visible before enrollment?

    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Resource {self.title} [{self.type}]>"


# ──────────────────────────────────────────────────────────────
#  Enrollment
# ──────────────────────────────────────────────────────────────

class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    status      = db.Column(db.String(32), default="active")  # active | completed | suspended
    progress    = db.Column(db.Float, default=0.0)             # 0.0 – 100.0 percent
    enrolled_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
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

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(255), nullable=False)
    description  = db.Column(db.Text)
    platform     = db.Column(db.String(64), default="zoom")  # zoom | teams | google_meet
    meeting_url  = db.Column(db.String(512))
    meeting_id   = db.Column(db.String(128))
    password     = db.Column(db.String(64))

    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration_min = db.Column(db.Integer, default=60)
    is_recorded  = db.Column(db.Boolean, default=False)
    recording_url = db.Column(db.String(512))
    status       = db.Column(db.String(32), default="scheduled")  # scheduled | live | ended

    course_id    = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<LiveSession '{self.title}' @ {self.scheduled_at}>"


# ──────────────────────────────────────────────────────────────
#  Certificate
# ──────────────────────────────────────────────────────────────

class Certificate(db.Model):
    __tablename__ = "certificates"

    id              = db.Column(db.Integer, primary_key=True)
    certificate_id  = db.Column(db.String(64), unique=True, nullable=False)  # e.g. PSFSLA-2024-00001
    student_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id       = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    issued_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    file_path       = db.Column(db.String(512))    # path to generated PDF
    is_valid        = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Certificate {self.certificate_id}>"


# ──────────────────────────────────────────────────────────────
#  Notification
# ──────────────────────────────────────────────────────────────

class Notification(db.Model):
    __tablename__ = "notifications"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title       = db.Column(db.String(255), nullable=False)
    message     = db.Column(db.Text)
    type        = db.Column(db.String(32), default="info")  # info | success | warning | danger
    is_read     = db.Column(db.Boolean, default=False)
    link        = db.Column(db.String(512))                 # optional action link
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Notification for user={self.user_id}: {self.title}>"


# ──────────────────────────────────────────────────────────────
#  CompletedResource  ← جديد
#  يسجّل أن طالباً معيناً قد أكمل مورداً معيناً في مساق معين.
# ──────────────────────────────────────────────────────────────

class CompletedResource(db.Model):
    __tablename__ = "completed_resources"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)
    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # العلاقات
    student  = db.relationship("User",     foreign_keys=[student_id])
    resource = db.relationship("Resource", foreign_keys=[resource_id])
    course   = db.relationship("Course",   foreign_keys=[course_id])

    __table_args__ = (
        # طالب لا يمكنه إكمال نفس المورد مرتين
        db.UniqueConstraint("student_id", "resource_id", name="uq_completed_resource"),
    )

    def __repr__(self):
        return f"<CompletedResource student={self.student_id} resource={self.resource_id}>"


# ──────────────────────────────────────────────────────────────
#  AttendedSession  ← جديد
#  يسجّل أن طالباً حضر جلسة مباشرة معينة.
# ──────────────────────────────────────────────────────────────

class AttendedSession(db.Model):
    __tablename__ = "attended_sessions"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id  = db.Column(db.Integer, db.ForeignKey("live_sessions.id"), nullable=False)
    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    attended_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # العلاقات
    student = db.relationship("User",        foreign_keys=[student_id])
    session = db.relationship("LiveSession", foreign_keys=[session_id])
    course  = db.relationship("Course",      foreign_keys=[course_id])

    __table_args__ = (
        # طالب لا يمكنه تسجيل حضور نفس الجلسة مرتين
        db.UniqueConstraint("student_id", "session_id", name="uq_attended_session"),
    )

    def __repr__(self):
        return f"<AttendedSession student={self.student_id} session={self.session_id}>"