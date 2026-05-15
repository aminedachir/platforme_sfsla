from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, Role
from app.auth.forms import LoginForm, RegisterForm, ForgotPasswordForm, WILAYAS
from datetime import datetime, timezone

auth_bp = Blueprint("auth", __name__)

def _redirect_by_role(user):
    if user.is_admin: return redirect(url_for("admin.dashboard"))
    elif user.is_professor: return redirect(url_for("professor.dashboard"))
    else: return redirect(url_for("student.dashboard"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated: return _redirect_by_role(current_user)
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("حسابك موقوف. يرجى التواصل مع الإدارة.", "danger")
                return redirect(url_for("auth.login"))
            if not user.is_approved:
                flash("حسابك قيد المراجعة من قبل الإدارة.", "warning")
                return redirect(url_for("auth.login"))
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else _redirect_by_role(user)
        else:
            flash("البريد الإلكتروني أو كلمة المرور غير صحيحة.", "danger")
    return render_template("auth/login.html", form=form)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated: return _redirect_by_role(current_user)
    form = RegisterForm()
    form.wilaya.choices = WILAYAS
    if form.validate_on_submit():
        role_name = form.role.data
        role = Role.query.filter_by(name=role_name).first()
        user = User(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip() or None,
            wilaya=form.wilaya.data or None,
            is_approved=(role_name == "student"),
        )
        user.set_password(form.password.data)
        if role: user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        if role_name == "professor":
            flash("تم إنشاء حسابك! سيتم مراجعة طلبك قريباً.", "success")
        else:
            flash("مرحباً بك! تم إنشاء حسابك بنجاح.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح.", "info")
    return redirect(url_for("main.index"))

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        flash("إذا كان البريد موجوداً، ستصل رسالة الاستعادة قريباً.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)
