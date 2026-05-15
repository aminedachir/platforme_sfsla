"""
app/admin/routes.py
-------------------
Admin Panel — PSFSLA
Routes: dashboard, users, courses, categories, analytics
"""

from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models import User, Role, Course, Enrollment, Category, Certificate, Notification, LiveSession
from app.admin.forms import CategoryForm, UserFilterForm

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ── Decorator: admin-only ─────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════

@admin_bp.route("/")
@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    # Core counts
    total_users      = User.query.count()
    total_students   = User.query.join(User.roles).filter(Role.name == "student").count()
    total_professors = User.query.join(User.roles).filter(Role.name == "professor").count()
    total_courses    = Course.query.count()
    published_courses = Course.query.filter_by(is_published=True).count()
    total_enrollments = Enrollment.query.count()
    total_certs      = Certificate.query.count()

    # Pending professors (not yet approved)
    pending_professors = (
        User.query
        .join(User.roles)
        .filter(Role.name == "professor", User.is_approved == False)
        .count()
    )

    # Recent users (last 5)
    recent_users = (
        User.query
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )

    # Recent enrollments (last 5)
    recent_enrollments = (
        Enrollment.query
        .order_by(Enrollment.enrolled_at.desc())
        .limit(5)
        .all()
    )

    # Enrollments per month (last 6 months) for sparkline
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
    monthly_enrollments = (
        db.session.query(
            func.strftime('%Y-%m', Enrollment.enrolled_at).label('month'),
            func.count(Enrollment.id).label('count')
        )
        .filter(Enrollment.enrolled_at >= six_months_ago)
        .group_by('month')
        .order_by('month')
        .all()
    )
    enroll_labels = [r.month for r in monthly_enrollments]
    enroll_data   = [r.count for r in monthly_enrollments]

    # Top 5 courses by enrollment
    top_courses = (
        db.session.query(Course, func.count(Enrollment.id).label('cnt'))
        .join(Enrollment, Enrollment.course_id == Course.id)
        .group_by(Course.id)
        .order_by(func.count(Enrollment.id).desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_students=total_students,
        total_professors=total_professors,
        total_courses=total_courses,
        published_courses=published_courses,
        total_enrollments=total_enrollments,
        total_certs=total_certs,
        pending_professors=pending_professors,
        recent_users=recent_users,
        recent_enrollments=recent_enrollments,
        enroll_labels=enroll_labels,
        enroll_data=enroll_data,
        top_courses=top_courses,
    )


# ══════════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════════

@admin_bp.route("/users")
@login_required
@admin_required
def users():
    form   = UserFilterForm(request.args, meta={"csrf": False})
    query  = User.query

    # Filter by role
    role_filter = request.args.get("role", "")
    if role_filter:
        query = query.join(User.roles).filter(Role.name == role_filter)

    # Filter by status
    status_filter = request.args.get("status", "")
    if status_filter == "active":
        query = query.filter(User.is_active == True)
    elif status_filter == "inactive":
        query = query.filter(User.is_active == False)
    elif status_filter == "pending":
        query = query.filter(User.is_approved == False)

    # Search
    search = request.args.get("q", "").strip()
    if search:
        query = query.filter(
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%"))  |
            (User.email.ilike(f"%{search}%"))
        )

    page  = request.args.get("page", 1, type=int)
    users_pag = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15)

    return render_template(
        "admin/users.html",
        users_pag=users_pag,
        form=form,
        role_filter=role_filter,
        status_filter=status_filter,
        search=search,
    )


@admin_bp.route("/users/<int:user_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    # Notify user
    notif = Notification(
        user_id=user.id,
        title="تمت الموافقة على حسابك",
        message="تهانينا! تمت الموافقة على حسابك كأستاذ. يمكنك الآن إنشاء التكوينات.",
        type="success",
    )
    db.session.add(notif)
    db.session.commit()
    flash(f"تمت الموافقة على حساب {user.full_name}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("لا يمكنك تعطيل حسابك الخاص.", "danger")
        return redirect(url_for("admin.users"))
    user.is_active = not user.is_active
    db.session.commit()
    state = "تفعيل" if user.is_active else "تعطيل"
    flash(f"تم {state} حساب {user.full_name}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("لا يمكنك حذف حسابك الخاص.", "danger")
        return redirect(url_for("admin.users"))
    db.session.delete(user)
    db.session.commit()
    flash(f"تم حذف المستخدم {user.full_name}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@admin_required
def change_role(user_id):
    user     = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    role_obj = Role.query.filter_by(name=new_role).first()
    if not role_obj:
        flash("الدور غير موجود.", "danger")
        return redirect(url_for("admin.users"))
    # Replace all roles with the single new role
    user.roles = [role_obj]
    db.session.commit()
    flash(f"تم تغيير دور {user.full_name} إلى {new_role}.", "success")
    return redirect(url_for("admin.users"))


# ══════════════════════════════════════════════════════════════
#  COURSES
# ══════════════════════════════════════════════════════════════

@admin_bp.route("/courses")
@login_required
@admin_required
def courses():
    search = request.args.get("q", "").strip()
    cat_id = request.args.get("category", type=int)
    status = request.args.get("status", "")

    query = Course.query

    if search:
        query = query.filter(
            (Course.title_fr.ilike(f"%{search}%")) |
            (Course.title_ar.ilike(f"%{search}%"))
        )
    if cat_id:
        query = query.filter(Course.category_id == cat_id)
    if status == "published":
        query = query.filter(Course.is_published == True)
    elif status == "draft":
        query = query.filter(Course.is_published == False)

    page = request.args.get("page", 1, type=int)
    courses_pag = query.order_by(Course.created_at.desc()).paginate(page=page, per_page=15)
    categories  = Category.query.order_by(Category.order).all()

    return render_template(
        "admin/courses.html",
        courses_pag=courses_pag,
        categories=categories,
        search=search,
        cat_id=cat_id,
        status=status,
    )


@admin_bp.route("/courses/<int:course_id>/toggle-publish", methods=["POST"])
@login_required
@admin_required
def toggle_publish(course_id):
    course = Course.query.get_or_404(course_id)
    course.is_published = not course.is_published
    db.session.commit()
    state = "نشر" if course.is_published else "إلغاء نشر"
    flash(f"تم {state} التكوين: {course.title_fr}.", "success")
    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash(f"تم حذف التكوين: {course.title_fr}.", "success")
    return redirect(url_for("admin.courses"))


# ══════════════════════════════════════════════════════════════
#  CATEGORIES
# ══════════════════════════════════════════════════════════════

@admin_bp.route("/categories", methods=["GET", "POST"])
@login_required
@admin_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(
            name_ar=form.name_ar.data,
            name_fr=form.name_fr.data,
            slug=form.slug.data,
            description=form.description.data,
            icon=form.icon.data or "bi-book",
            color=form.color.data or "#1B2A52",
            order=form.order.data or 0,
        )
        db.session.add(cat)
        db.session.commit()
        flash(f"تم إضافة التصنيف: {cat.name_fr}.", "success")
        return redirect(url_for("admin.categories"))

    all_cats = Category.query.order_by(Category.order).all()
    return render_template("admin/categories.html", form=form, categories=all_cats)


@admin_bp.route("/categories/<int:cat_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_category(cat_id):
    cat  = Category.query.get_or_404(cat_id)
    form = CategoryForm(obj=cat)
    if form.validate_on_submit():
        form.populate_obj(cat)
        db.session.commit()
        flash(f"تم تعديل التصنيف: {cat.name_fr}.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/categories.html",
                           form=form, categories=Category.query.order_by(Category.order).all(),
                           editing=cat)


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.courses.count() > 0:
        flash("لا يمكن حذف تصنيف يحتوي على تكوينات.", "danger")
        return redirect(url_for("admin.categories"))
    db.session.delete(cat)
    db.session.commit()
    flash(f"تم حذف التصنيف: {cat.name_fr}.", "success")
    return redirect(url_for("admin.categories"))


# ══════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════

@admin_bp.route("/analytics")
@login_required
@admin_required
def analytics():
    # Enrollments by month (last 12)
    twelve_ago = datetime.now(timezone.utc) - timedelta(days=365)
    monthly = (
        db.session.query(
            func.strftime('%Y-%m', Enrollment.enrolled_at).label('month'),
            func.count(Enrollment.id).label('count')
        )
        .filter(Enrollment.enrolled_at >= twelve_ago)
        .group_by('month')
        .order_by('month')
        .all()
    )
    enroll_labels = [r.month for r in monthly]
    enroll_data   = [r.count for r in monthly]

    # Users by role
    roles_data = (
        db.session.query(Role.name, func.count(User.id).label('cnt'))
        .join(Role.users)
        .group_by(Role.name)
        .all()
    )
    role_labels = [r.name for r in roles_data]
    role_counts = [r.cnt  for r in roles_data]

    # Courses by category
    cats_data = (
        db.session.query(Category.name_fr, func.count(Course.id).label('cnt'))
        .join(Course, Course.category_id == Category.id)
        .group_by(Category.id)
        .order_by(func.count(Course.id).desc())
        .limit(8)
        .all()
    )
    cat_labels = [r.name_fr for r in cats_data]
    cat_counts = [r.cnt    for r in cats_data]

    # Enrollment status breakdown
    status_data = (
        db.session.query(Enrollment.status, func.count(Enrollment.id).label('cnt'))
        .group_by(Enrollment.status)
        .all()
    )
    status_labels = [r.status for r in status_data]
    status_counts = [r.cnt   for r in status_data]

    # Top professors by student count
    top_professors = (
        db.session.query(User, func.count(Enrollment.id).label('students'))
        .join(Course, Course.professor_id == User.id)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .group_by(User.id)
        .order_by(func.count(Enrollment.id).desc())
        .limit(5)
        .all()
    )

    # Summary numbers
    total_revenue    = db.session.query(func.sum(Course.price)).scalar() or 0
    avg_progress     = db.session.query(func.avg(Enrollment.progress)).scalar() or 0
    completed_count  = Enrollment.query.filter_by(status="completed").count()

    return render_template(
        "admin/analytics.html",
        enroll_labels=enroll_labels,
        enroll_data=enroll_data,
        role_labels=role_labels,
        role_counts=role_counts,
        cat_labels=cat_labels,
        cat_counts=cat_counts,
        status_labels=status_labels,
        status_counts=status_counts,
        top_professors=top_professors,
        total_revenue=total_revenue,
        avg_progress=round(avg_progress, 1),
        completed_count=completed_count,
    )


# ══════════════════════════════════════════════════════════════
#  CERTIFICATES  (view only)
# ══════════════════════════════════════════════════════════════

@admin_bp.route("/certificates")
@login_required
@admin_required
def certificates():
    page  = request.args.get("page", 1, type=int)
    certs = Certificate.query.order_by(Certificate.issued_at.desc()).paginate(page=page, per_page=20)
    return render_template("admin/certificates.html", certs=certs)


@admin_bp.route("/certificates/<int:cert_id>/revoke", methods=["POST"])
@login_required
@admin_required
def revoke_certificate(cert_id):
    cert = Certificate.query.get_or_404(cert_id)
    cert.is_valid = not cert.is_valid
    db.session.commit()
    state = "تفعيل" if cert.is_valid else "إلغاء"
    flash(f"تم {state} الشهادة {cert.certificate_id}.", "success")
    return redirect(url_for("admin.certificates"))