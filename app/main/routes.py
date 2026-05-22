from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Course, Category

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    categories = Category.query.order_by(Category.order).all()
    featured   = Course.query.filter_by(is_published=True).limit(6).all()
    return render_template("main/index.html",
                           categories=categories,
                           featured=featured)

@main_bp.route("/about")
def about():
    from app.models import User, Course, Certificate, Role
    from sqlalchemy import func
    
    # إحصائيات للمنصة
    stats = {
        'students': User.query.join(User.roles).filter(Role.name == 'student').count(),
        'professors': User.query.join(User.roles).filter(Role.name == 'professor').count(),
        'courses': Course.query.filter_by(is_published=True).count(),
        'certificates': Certificate.query.count(),
    }
    
    # فريق الأساتذة (اختياري)
    professor_role = Role.query.filter_by(name='professor').first()
    team_members = []
    if professor_role:
        team_members = User.query.filter(User.roles.any(id=professor_role.id)).limit(6).all()
    
    return render_template("main/about.html", stats=stats, team_members=team_members)

@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        subject = request.form.get("subject")
        message = request.form.get("message")
        
        # حفظ الرسالة في قاعدة البيانات (اختياري)
        # أو إرسال بريد إلكتروني للمدير
        
        flash("شكراً لتواصلك! سنرد عليك في أقرب وقت.", "success")
        return redirect(url_for("main.contact"))
    
    return render_template("main/contact.html")


@main_bp.route("/verify/<certificate_id>")
def verify_certificate(certificate_id):
    """
    Public verification page — no login required.
    URL:  /verify/PSFSLA-2024-00001
    """
    from app.models import Certificate  
 
    cert = Certificate.query.filter_by(
        certificate_id=certificate_id
    ).first()
 
    return render_template(
        "public/verify_certificate.html",
        cert=cert,
        certificate_id=certificate_id,
    )
 
