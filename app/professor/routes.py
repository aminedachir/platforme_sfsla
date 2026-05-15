"""
app/professor/routes.py
-----------------------
Professor dashboard routes for PSFSLA.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Course, Resource, LiveSession, Enrollment, User
from app.professor.forms import CourseForm, ResourceForm, LiveSessionForm
from functools import wraps
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
from werkzeug.datastructures import FileStorage

professor_bp = Blueprint("professor", __name__, url_prefix="/professor")


def professor_required(f):
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
    courses = current_user.courses_taught.all()
    course_ids = [c.id for c in courses]

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

    recent_courses = (
        current_user.courses_taught
        .order_by(Course.created_at.desc())
        .limit(5)
        .all()
    )

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

def save_uploaded_file(file, subfolder="thumbnails"):
    """Helper function to save uploaded files"""
    if not file or not file.filename:
        return None
    filename = secure_filename(file.filename)
    # Create unique filename with timestamp
    name, ext = os.path.splitext(filename)
    filename = f"{int(datetime.now().timestamp())}_{name}{ext}"
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder, filename)
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)
    file.save(upload_path)
    return filename


@professor_bp.route("/courses/create", methods=["GET", "POST"])
@login_required
@professor_required
def create_course():
    form = CourseForm()
    
    from app.models import Category
    form.category_id.choices = [(0, "--- اختر تصنيفاً ---")] + [(c.id, c.name_ar) for c in Category.query.order_by(Category.name_ar).all()]
    
    if form.validate_on_submit():
        from werkzeug.datastructures import FileStorage
        
        course = Course(
            title_ar=form.title_ar.data,
            title_fr=form.title_fr.data,
            description=form.description.data,
            level=form.level.data,
            duration_hours=form.duration_hours.data,
            category_id=form.category_id.data if form.category_id.data and form.category_id.data != 0 else None,
            is_published=form.is_published.data,
            is_free=form.is_free.data,
            price=form.price.data if not form.is_free.data else 0,
            professor_id=current_user.id,
        )
        
        if form.thumbnail.data and isinstance(form.thumbnail.data, FileStorage):
            if form.thumbnail.data.filename:
                thumbnail = save_uploaded_file(form.thumbnail.data, "thumbnails")
                if thumbnail:
                    course.thumbnail = thumbnail

        db.session.add(course)
        db.session.commit()
        flash("✅ تم إنشاء التكوين بنجاح!", "success")
        return redirect(url_for("professor.my_courses"))
    
    return render_template("professor/course_form.html", form=form, mode="create", course=None)


# ──────────────────────────────────────────────────────────────
#  Edit Course
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
@professor_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)

    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)

    form = CourseForm(obj=course)
    
    from app.models import Category
    form.category_id.choices = [(0, "--- اختر تصنيفاً ---")] + [(c.id, c.name_ar) for c in Category.query.order_by(Category.name_ar).all()]
    form.category_id.data = course.category_id or 0
    
    if form.validate_on_submit():
        from werkzeug.datastructures import FileStorage
        
        course.title_ar = form.title_ar.data
        course.title_fr = form.title_fr.data
        course.description = form.description.data
        course.level = form.level.data
        course.duration_hours = form.duration_hours.data
        course.category_id = form.category_id.data if form.category_id.data and form.category_id.data != 0 else None
        course.is_published = form.is_published.data
        course.is_free = form.is_free.data
        if not form.is_free.data:
            course.price = form.price.data
        else:
            course.price = 0

        # ✅ التحقق الصحيح من الملف
        if form.thumbnail.data and isinstance(form.thumbnail.data, FileStorage):
            if form.thumbnail.data.filename:
                thumbnail = save_uploaded_file(form.thumbnail.data, "thumbnails")
                if thumbnail:
                    course.thumbnail = thumbnail

        db.session.commit()
        flash("✅ تم تحديث التكوين بنجاح!", "success")
        return redirect(url_for("professor.my_courses"))

    return render_template("professor/course_form.html", form=form, mode="edit", course=course)


# ──────────────────────────────────────────────────────────────
#  Delete Course
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
@professor_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)

    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)

    db.session.delete(course)
    db.session.commit()
    flash("🗑️ تم حذف التكوين بنجاح.", "success")
    return redirect(url_for("professor.my_courses"))


# ──────────────────────────────────────────────────────────────
#  Manage Resources
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses/<int:course_id>/resources", methods=["GET", "POST"])
@login_required
@professor_required
def manage_resources(course_id):
    course = Course.query.get_or_404(course_id)

    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)

    form = ResourceForm()
    if form.validate_on_submit():
        from werkzeug.datastructures import FileStorage
        
        resource = Resource(
            title=form.title.data,
            type=form.type.data,
            url=form.url.data if form.type.data != 'pdf' else None,
            description=form.description.data,
            is_public=form.is_public.data,
            order=form.order.data or 0,
            course_id=course.id,
        )
        
        # ✅ التحقق الصحيح من الملف
        if form.file.data and isinstance(form.file.data, FileStorage):
            if form.file.data.filename:
                filename = save_uploaded_file(form.file.data, "resources")
                if filename:
                    resource.file_path = filename

        db.session.add(resource)
        db.session.commit()
        flash("📄 تمت إضافة المورد بنجاح!", "success")
        return redirect(url_for("professor.manage_resources", course_id=course.id))

    resources = course.resources.order_by(Resource.order).all()
    return render_template(
        "professor/resources.html",
        course=course,
        resources=resources,
        form=form,
    )


@professor_bp.route("/resources/<int:resource_id>/delete", methods=["POST"])
@login_required
@professor_required
def delete_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    course = resource.course

    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)

    db.session.delete(resource)
    db.session.commit()
    flash("🗑️ تم حذف المورد.", "success")
    return redirect(url_for("professor.manage_resources", course_id=course.id))


# ──────────────────────────────────────────────────────────────
#  Live Sessions
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/courses/<int:course_id>/sessions")
@login_required
@professor_required
def list_live_sessions(course_id):
    course = Course.query.get_or_404(course_id)
    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    sessions = course.live_sessions.order_by(LiveSession.scheduled_at.desc()).all()
    return render_template("professor/live_sessions.html", course=course, sessions=sessions)


@professor_bp.route("/courses/<int:course_id>/sessions/add", methods=["GET", "POST"])
@login_required
@professor_required
def add_live_session(course_id):
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
        flash("🎥 تمت إضافة الجلسة المباشرة!", "success")
        return redirect(url_for("professor.list_live_sessions", course_id=course.id))

    return render_template("professor/live_session_form.html", form=form, course=course)


@professor_bp.route("/sessions/<int:session_id>/delete", methods=["POST"])
@login_required
@professor_required
def delete_live_session(session_id):
    session = LiveSession.query.get_or_404(session_id)
    course_id = session.course_id
    course = session.course
    
    if course.professor_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    db.session.delete(session)
    db.session.commit()
    flash("🗑️ تم حذف الجلسة.", "success")
    return redirect(url_for("professor.list_live_sessions", course_id=course_id))


# ──────────────────────────────────────────────────────────────
#  Students
# ──────────────────────────────────────────────────────────────

@professor_bp.route("/students")
@login_required
@professor_required
def students():
    course_ids = [c.id for c in current_user.courses_taught.all()]
    
    # Get all enrollments with student and course info
    enrollments = []
    if course_ids:
        enrollments = (
            db.session.query(Enrollment, User, Course)
            .join(User, Enrollment.student_id == User.id)
            .join(Course, Enrollment.course_id == Course.id)
            .filter(Enrollment.course_id.in_(course_ids))
            .order_by(Enrollment.enrolled_at.desc())
            .all()
        )
    
    return render_template("professor/students.html", enrollments=enrollments)