from flask import (Blueprint, render_template, redirect, url_for,
                   flash, abort, request, current_app, send_file, Response)
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Course, Enrollment, Certificate, Notification, LiveSession
from datetime import datetime, timezone
import io
import os

student_bp = Blueprint("student", __name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Dashboard
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route("/")
@student_bp.route("/dashboard")
@login_required
def dashboard():
    enrollments   = current_user.enrollments.all()
    completed     = [e for e in enrollments if e.status == "completed"]
    active        = [e for e in enrollments if e.status == "active"]
    certificates  = current_user.certificates.all()
    notifications = (current_user.notifications
                     .order_by(Notification.created_at.desc()).limit(5).all())
    course_ids = [e.course_id for e in enrollments]
    upcoming = (LiveSession.query
                .filter(LiveSession.course_id.in_(course_ids),
                        LiveSession.scheduled_at >= datetime.now(timezone.utc),
                        LiveSession.status == "scheduled")
                .order_by(LiveSession.scheduled_at).limit(3).all()
                if course_ids else [])
    return render_template(
        "student/dashboard.html",
        enrollments=enrollments, active=active, completed=completed,
        certificates=certificates, notifications=notifications,
        upcoming=upcoming,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  My Courses
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route("/courses")
@login_required
def my_courses():
    status      = request.args.get("status", "all")
    enrollments = current_user.enrollments.all()

    if status == "active":
        enrollments = [e for e in enrollments if e.status == "active"]
    elif status == "completed":
        enrollments = [e for e in enrollments if e.status == "completed"]

    return render_template(
        "student/my_courses.html",
        enrollments=enrollments,
        status_filter=status,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  My Certificates list
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route("/certificates")
@login_required
def my_certificates():
    certificates = current_user.certificates.all()
    return render_template("student/certificates.html", certificates=certificates)


# ─────────────────────────────────────────────────────────────────────────────
#  Enroll
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route("/enroll/<int:course_id>", methods=["POST"])
@login_required
def enroll(course_id):
    course   = Course.query.get_or_404(course_id)
    existing = Enrollment.query.filter_by(
        student_id=current_user.id, course_id=course_id
    ).first()
    if existing:
        flash("أنت مسجل في هذا التكوين مسبقاً.", "warning")
    else:
        db.session.add(Enrollment(student_id=current_user.id, course_id=course_id))
        db.session.add(Notification(
            user_id=current_user.id,
            title="تسجيل ناجح",
            message=f"تم تسجيلك في تكوين: {course.title_ar}",
            type="success",
        ))
        db.session.commit()
        flash(f"تم التسجيل في «{course.title_ar}» بنجاح!", "success")
    return redirect(url_for("courses.detail", course_id=course_id))

# ─────────────────────────────────────────────────────────────────────────────
#  Update Progress
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route("/update-progress/<int:course_id>", methods=["POST"])
@login_required
def update_progress(course_id):
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
    ).first_or_404()

    try:
        progress = float(request.form.get("progress", 0))
    except (TypeError, ValueError):
        progress = 0.0

    progress = max(0.0, min(100.0, progress))
    enrollment.progress = progress

    # فقط تحديث النسبة — لا تغيير الـ status هنا
    # الـ status يتغير فقط عبر زر "إصدار الشهادة" في complete_course
    db.session.commit()
    flash(f"تم تحديث تقدمك إلى {progress:.0f}%.", "info")
    return redirect(url_for("courses.detail", course_id=course_id))


# ─────────────────────────────────────────────────────────────────────────────
#  Complete course & issue certificate  (POST /complete/<course_id>)
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route("/complete/<int:course_id>", methods=["POST"])
@login_required
def complete_course(course_id):
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
    ).first_or_404()

    if enrollment.progress < 100.0:
        flash("يجب إكمال جميع موارد التكوين قبل إصدار الشهادة (التقدم 100%).", "warning")
        return redirect(url_for("courses.detail", course_id=course_id))

    # تحقق إذا كانت الشهادة موجودة مسبقاً
    existing_cert = Certificate.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
    ).first()

    if existing_cert:
        flash("لقد حصلت على شهادتك مسبقاً.", "info")
        return redirect(url_for("student.my_certificates"))

    # ── Mark completed ────────────────────────────────────────
    enrollment.status       = "completed"
    enrollment.completed_at = datetime.now(timezone.utc)

    # ── Generate certificate ──────────────────────────────────
    from app.utils.certificate import issue_certificate

    base_url = request.host_url.rstrip("/")
    save_dir = current_app.config.get(
        "CERT_FOLDER",
        os.path.join(current_app.static_folder, "certificates"),
    )
    os.makedirs(save_dir, exist_ok=True)

    cert = issue_certificate(enrollment, base_url=base_url, save_dir=save_dir)

    # ── Notification ──────────────────────────────────────────
    db.session.add(Notification(
        user_id=current_user.id,
        title="🎓 تهانينا! لقد حصلت على شهادتك",
        message=(
            f"تم إصدار شهادة إتمام تكوين «{enrollment.course.title_ar}» "
            f"برقم {cert.certificate_id}"
        ),
        type="success",
        link=url_for("student.my_certificates"),
    ))

    db.session.commit()
    flash(f"تهانينا! تم إصدار شهادتك برقم {cert.certificate_id}", "success")
    return redirect(url_for("student.my_certificates"))


# ─────────────────────────────────────────────────────────────────────────────
#  Download certificate PDF  (GET /certificates/download/<id>)
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route("/certificates/download/<int:cert_id>")
@login_required
def download_certificate(cert_id):
    """
    Stream the certificate PDF to the browser.
    Regenerates on the fly if the file is missing (e.g. after a server move).
    Only the certificate holder may download it.
    """
    cert = Certificate.query.get_or_404(cert_id)

    # Ownership check
    if cert.student_id != current_user.id and not current_user.is_admin:
        abort(403)

    if not cert.is_valid:
        flash("هذه الشهادة غير صالحة أو تم إلغاؤها.", "danger")
        return redirect(url_for("student.my_certificates"))

    # ── Try to serve saved file first ─────────────────────────
    save_dir = current_app.config.get(
        "CERT_FOLDER",
        os.path.join(current_app.static_folder, "certificates"),
    )
    if cert.file_path:
        # file_path stored relative to save_dir parent  (e.g. "certificates/PSFSLA-…pdf")
        abs_path = os.path.join(
            current_app.static_folder,
            cert.file_path.lstrip("/"),
        )
        if os.path.exists(abs_path):
            return send_file(
                abs_path,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"{cert.certificate_id}.pdf",
            )

    # ── Regenerate on the fly ─────────────────────────────────
    from app.utils.certificate import generate_certificate_pdf

    enrollment = Enrollment.query.filter_by(
        student_id=cert.student_id,
        course_id=cert.course_id,
    ).first()

    course  = cert.course
    student = cert.holder
    prof    = course.professor if course else None

    base_url   = request.host_url.rstrip("/")
    verify_url = f"{base_url}/verify/{cert.certificate_id}"

    pdf_bytes = generate_certificate_pdf(
        student_full_name=student.full_name,
        course_title_ar=course.title_ar  if course else "",
        course_title_fr=course.title_fr  if course else "",
        certificate_id=cert.certificate_id,
        issued_at=cert.issued_at,
        professor_name=prof.full_name    if prof    else "",
        duration_hours=course.duration_hours if course else 0,
        verify_url=verify_url,
    )

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{cert.certificate_id}.pdf"'
            )
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Profile
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.first_name = request.form.get("first_name", current_user.first_name)
        current_user.last_name  = request.form.get("last_name",  current_user.last_name)
        current_user.phone      = request.form.get("phone",      current_user.phone)
        current_user.wilaya     = request.form.get("wilaya",     current_user.wilaya)
        current_user.bio        = request.form.get("bio",        current_user.bio)

        if "avatar" in request.files:
            file = request.files["avatar"]
            if file and file.filename:
                from werkzeug.utils import secure_filename
                filename  = secure_filename(f"{current_user.id}_{file.filename}")
                file_path = os.path.join(
                    current_app.config["UPLOAD_FOLDER"], filename
                )
                file.save(file_path)
                current_user.avatar = filename

        db.session.commit()
        flash("تم تحديث الملف الشخصي بنجاح", "success")
        return redirect(url_for("student.profile"))

    from app.auth.forms import WILAYAS
    return render_template("student/profile.html",
                           user=current_user, wilayas=WILAYAS)


# ─────────────────────────────────────────────────────────────────────────────
#  Mark all notifications read
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_notifications_read():
    Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).update({"is_read": True})
    db.session.commit()
    flash("تم تحديث جميع الإشعارات كمقروءة", "success")
    return redirect(request.referrer or url_for("student.dashboard"))