from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Course, Enrollment, Certificate, Notification, LiveSession
from datetime import datetime, timezone

student_bp = Blueprint("student", __name__)

@student_bp.route("/")
@student_bp.route("/dashboard")
@login_required
def dashboard():
    enrollments  = current_user.enrollments.all()
    completed    = [e for e in enrollments if e.status == "completed"]
    active       = [e for e in enrollments if e.status == "active"]
    certificates = current_user.certificates.all()
    notifications= current_user.notifications.order_by(Notification.created_at.desc()).limit(5).all()
    course_ids   = [e.course_id for e in enrollments]
    upcoming = (LiveSession.query
                .filter(LiveSession.course_id.in_(course_ids),
                        LiveSession.scheduled_at >= datetime.now(timezone.utc),
                        LiveSession.status == "scheduled")
                .order_by(LiveSession.scheduled_at).limit(3).all() if course_ids else [])
    return render_template("student/dashboard.html",
        enrollments=enrollments, active=active, completed=completed,
        certificates=certificates, notifications=notifications, upcoming=upcoming)

@student_bp.route("/courses")
@login_required
def my_courses():
    status = request.args.get('status', 'all')
    enrollments = current_user.enrollments.all()
    
    if status == 'active':
        enrollments = [e for e in enrollments if e.status == 'active']
    elif status == 'completed':
        enrollments = [e for e in enrollments if e.status == 'completed']
    
    return render_template("student/my_courses.html", 
                         enrollments=enrollments, 
                         status_filter=status)

@student_bp.route("/certificates")
@login_required
def my_certificates():
    certificates = current_user.certificates.all()
    return render_template("student/certificates.html", certificates=certificates)

@student_bp.route("/enroll/<int:course_id>", methods=["POST"])
@login_required
def enroll(course_id):
    course   = Course.query.get_or_404(course_id)
    existing = Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first()
    if existing:
        flash("أنت مسجل في هذا التكوين مسبقاً.", "warning")
    else:
        db.session.add(Enrollment(student_id=current_user.id, course_id=course_id))
        db.session.add(Notification(user_id=current_user.id, title="تسجيل ناجح",
            message=f"تم تسجيلك في تكوين: {course.title_ar}", type="success"))
        db.session.commit()
        flash(f"تم التسجيل في «{course.title_ar}» بنجاح!", "success")
    return redirect(url_for("courses.detail", course_id=course_id))


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """عرض وتعديل الملف الشخصي للطالب"""
    if request.method == "POST":
        # تحديث البيانات
        current_user.first_name = request.form.get("first_name", current_user.first_name)
        current_user.last_name = request.form.get("last_name", current_user.last_name)
        current_user.phone = request.form.get("phone", current_user.phone)
        current_user.wilaya = request.form.get("wilaya", current_user.wilaya)
        current_user.bio = request.form.get("bio", current_user.bio)
        
        # معالجة رفع الصورة
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                import os
                filename = secure_filename(f"{current_user.id}_{file.filename}")
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                current_user.avatar = filename
        
        db.session.commit()
        flash("تم تحديث الملف الشخصي بنجاح", "success")
        return redirect(url_for("student.profile"))
    
    # استعراض الولايات للقائمة المنسدلة
    from app.auth.forms import WILAYAS
    return render_template("student/profile.html", user=current_user, wilayas=WILAYAS)


@student_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("تم تحديث جميع الإشعارات كمقروءة", "success")
    return redirect(request.referrer or url_for("student.dashboard"))
