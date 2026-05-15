"""
app/professor/routes.py
-----------------------
Professor dashboard routes for PSFSLA.
All routes require login + professor or admin role.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Course, Resource, LiveSession, Enrollment, User
from app.professor.forms import CourseForm, ResourceForm, LiveSessionForm
from functools import wraps
import os
from werkzeug.utils import secure_filename

professor_bp = Blueprint("professor", __name__, url_prefix="/professor")


# ──────────────────────────────────────────────────────────────
#  Access decorator
# ──────────────────────────────────────────────────────────────

def professor_required(f):
    """Allow access only to professors and admins."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not (current_user.is_professor or current_user.is_admin):
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────────────────
#  Dashboard
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/")
@professor_bp.route("/dashboard")
@login_required
@professor_required
def dashboard():
    """Main professor dashboard with statistics."""
    courses = current_user.courses_taught.all()
    course_ids = [c.id for c in courses]

    # Statistics
    total_courses = len(courses)
    total_students = (
        db.session.query(Enrollment.student_id)
        .filter(Enrollment.course_id.in_(course_ids))
        .distinct()
        .count()
        if course_ids else 0
    )
    total_sessions = (
        LiveSession.query.filter(LiveSession.course_id.in_(course_ids)).count()
        if course_ids else 0
    )
    published_courses = sum(1 for c in courses if c.is_published)

    # Recent courses (last 5)
    recent_courses = (
        current_user.courses_taught
        .order_by(Course.created_at.desc())
        .limit(5)
        .all()
    )

    # Upcoming live sessions
    from datetime import datetime, timezone
    upcoming_sessions = (
        LiveSession.query
        .filter(
            LiveSession.course_id.in_(course_ids),
            LiveSession.scheduled_at >= datetime.now(timezone.utc),
            LiveSession.status == "scheduled"
        )
        .order_by(LiveSession.scheduled_at)
        .limit(5)
        .all()
        if course_ids else []
    )

    stats = {
        "total_courses": total_courses,
        "total_students": total_students,
        "total_sessions": total_sessions,
        "published_courses": published_courses,
    }

    return render_template(
        "professor/dashboard.html",
        stats=stats,
        recent_courses=recent_courses,
        upcoming_sessions=upcoming_sessions,
    )


# ──────────────────────────────────────────────────────────────
#  My Courses
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses")
@login_required
@professor_required
def my_courses():
    """List all courses taught by the current professor."""
    page = request.args.get("page", 1, type=int)
    courses = (
        current_user.courses_taught
        .order_by(Course.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )
    return render_template("professor/my_courses.html", courses=courses)


# ──────────────────────────────────────────────────────────────
#  Create Course
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses/create", methods=["GET", "POST"])
@login_required
@professor_required
def create_course():
    """Form to add a new course."""
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(
            title_ar=form.title_ar.data,
            title_fr=form.title_fr.data,
            description=form.description.data,
            level=form.level.data,
            duration_hours=form.duration_hours.data,
            category_id=form.category_id.data if form.category_id.data else None,
            is_published=form.is_published.data,
            professor_id=current_user.id,
        )
        # Handle thumbnail upload
        if form.thumbnail.data:
            filename = secure_filename(form.thumbnail.data.filename)
            upload_path = os.path.join("app", "static", "uploads", "thumbnails", filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            form.thumbnail.data.save(upload_path)
            course.thumbnail = filename

        db.session.add(course)
        db.session.commit()
        flash("تم إنشاء التكوين بنجاح!", "success")
        return redirect(url_for("professor.my_courses"))

    return render_template("professor/course_form.html", form=form, mode="create")


# ──────────────────────────────────────────────────────────────
#  Edit Course
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
@professor_required
def edit_course(course_id):
    """Edit an existing course."""
    course = Course.query.get_or_404(course_id)

    # Only the owning professor or admin can edit
    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)

    form = CourseForm(obj=course)
    if form.validate_on_submit():
        course.title_ar = form.title_ar.data
        course.title_fr = form.title_fr.data
        course.description = form.description.data
        course.level = form.level.data
        course.duration_hours = form.duration_hours.data
        course.category_id = form.category_id.data if form.category_id.data else None
        course.is_published = form.is_published.data

        if form.thumbnail.data and hasattr(form.thumbnail.data, "filename"):
            filename = secure_filename(form.thumbnail.data.filename)
            if filename:
                upload_path = os.path.join("app", "static", "uploads", "thumbnails", filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                form.thumbnail.data.save(upload_path)
                course.thumbnail = filename

        db.session.commit()
        flash("تم تحديث التكوين بنجاح!", "success")
        return redirect(url_for("professor.my_courses"))

    return render_template("professor/course_form.html", form=form, mode="edit", course=course)


# ──────────────────────────────────────────────────────────────
#  Delete Course
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
@professor_required
def delete_course(course_id):
    """Delete a course (cascade deletes resources, sessions, enrollments)."""
    course = Course.query.get_or_404(course_id)

    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)

    db.session.delete(course)
    db.session.commit()
    flash("تم حذف التكوين بنجاح.", "success")
    return redirect(url_for("professor.my_courses"))


# ──────────────────────────────────────────────────────────────
#  Manage Resources
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses/<int:course_id>/resources", methods=["GET", "POST"])
@login_required
@professor_required
def manage_resources(course_id):
    """Add/remove resources for a course."""
    course = Course.query.get_or_404(course_id)

    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)

    form = ResourceForm()
    if form.validate_on_submit():
        resource = Resource(
            title=form.title.data,
            type=form.type.data,
            url=form.url.data,
            description=form.description.data,
            is_public=form.is_public.data,
            order=form.order.data or 0,
            course_id=course.id,
        )
        # Handle file upload
        if form.file.data and hasattr(form.file.data, "filename"):
            filename = secure_filename(form.file.data.filename)
            if filename:
                upload_path = os.path.join("app", "static", "uploads", "resources", filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                form.file.data.save(upload_path)
                resource.file_path = filename

        db.session.add(resource)
        db.session.commit()
        flash("تمت إضافة المورد بنجاح!", "success")
        return redirect(url_for("professor.manage_resources", course_id=course.id))

    resources = course.resources.order_by(Resource.order).all()
    return render_template(
        "professor/manage_resources.html",
        course=course,
        resources=resources,
        form=form,
    )


@professor_bp.route("/resources/<int:resource_id>/delete", methods=["POST"])
@login_required
@professor_required
def delete_resource(resource_id):
    """Delete a single resource."""
    resource = Resource.query.get_or_404(resource_id)
    course = resource.course

    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)

    db.session.delete(resource)
    db.session.commit()
    flash("تم حذف المورد.", "success")
    return redirect(url_for("professor.manage_resources", course_id=course.id))


# ──────────────────────────────────────────────────────────────
#  Live Sessions
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses/<int:course_id>/sessions/add", methods=["GET", "POST"])
@login_required
@professor_required
def add_live_session(course_id):
    """Add a live session to a course."""
    course = Course.query.get_or_404(course_id)

    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)

    form = LiveSessionForm()
    if form.validate_on_submit():
        session = LiveSession(
            title=form.title.data,
            description=form.description.data,
            platform=form.platform.data,
            meeting_url=form.meeting_url.data,
            meeting_id=form.meeting_id.data,
            password=form.password.data,
            scheduled_at=form.scheduled_at.data,
            duration_min=form.duration_min.data,
            course_id=course.id,
        )
        db.session.add(session)
        db.session.commit()
        flash("تمت إضافة الجلسة المباشرة!", "success")
        return redirect(url_for("professor.my_courses"))

    return render_template(
        "professor/live_session_form.html",
        form=form,
        course=course,
    )


# ──────────────────────────────────────────────────────────────
#  Students
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/students")
@login_required
@professor_required
def students():
    """View all students enrolled in the professor's courses."""
    course_ids = [c.id for c in current_user.courses_taught.all()]

    if not course_ids:
        enrollments = []
    else:
        enrollments = (
            db.session.query(Enrollment, User, Course)
            .join(User, Enrollment.student_id == User.id)
            .join(Course, Enrollment.course_id == Course.id)
            .filter(Enrollment.course_id.in_(course_ids))
            .order_by(Enrollment.enrolled_at.desc())
            .all()
        )

    return render_template("professor/students.html", enrollments=enrollments)