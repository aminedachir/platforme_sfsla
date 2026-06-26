"""
app/__init__.py
---------------
Application factory for PSFSLA.
"""

import os
from flask import Flask, request
from flask_login import current_user
from config.settings import config
from app.extensions import db, login_manager, migrate, mail
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

csrf = CSRFProtect()


def create_app(config_name: str = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config[config_name])

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.main.routes import main_bp
    from app.auth.routes import auth_bp
    from app.student.routes import student_bp
    from app.professor.routes import professor_bp
    from app.courses.routes import courses_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(professor_bp, url_prefix="/professor")
    app.register_blueprint(courses_bp, url_prefix="/courses")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Context processors ──────────────────────────────────
    @app.context_processor
    def inject_current_user():
        return dict(current_user=current_user, lang="ar")

    # ── معالجة أخطاء قاعدة البيانات ───────────────────────
    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(e):
        """معالجة أخطاء قاعدة البيانات وإلغاء المعاملة الفاشلة"""
        db.session.rollback()
        app.logger.error(f"Database error: {e}")
        return render_error_template(500)

    @app.errorhandler(Exception)
    def handle_generic_error(e):
        """معالجة أي خطأ عام"""
        db.session.rollback()
        app.logger.error(f"Error: {e}")
        return render_error_template(500)

    # ── تأكد من إغلاق الجلسة بعد كل طلب ──────────────────
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """إزالة الجلسة بعد كل طلب"""
        if exception:
            db.session.rollback()
        db.session.remove()

    # ── إعادة محاولة الاتصال بقاعدة البيانات ─────────────
    @app.before_request
    def before_request():
        """التحقق من اتصال قاعدة البيانات قبل كل طلب"""
        try:
            # محاولة تنفيذ استعلام بسيط
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.warning(f"Database connection issue: {e}")

    # ── دالة مساعدة لعرض قالب الخطأ ─────────────────────
    def render_error_template(status_code):
        """عرض قالب الخطأ المناسب"""
        from flask import render_template
        if status_code == 403:
            return render_template("errors/403.html"), 403
        elif status_code == 404:
            return render_template("errors/404.html"), 404
        else:
            return render_template("errors/500.html"), 500

    # ── تسجيل معالجات الأخطاء ────────────────────────────
    _register_error_handlers(app)

    # ── إنشاء قاعدة البيانات ──────────────────────────────
    with app.app_context():
        try:
            db.create_all()
            _seed_initial_data()
        except SQLAlchemyError as e:
            app.logger.error(f"Error creating database: {e}")
            db.session.rollback()

    return app


def _register_error_handlers(app: Flask):
    from flask import render_template

    @app.errorhandler(403)
    def forbidden(e):
        db.session.rollback()
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def _seed_initial_data():
    """Create default roles and admin user on first run."""
    from app.models import Role, User
    import os
    from sqlalchemy.exc import SQLAlchemyError

    try:
        # Create roles
        for role_name in ["admin", "professor", "student"]:
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name, description=f"Role: {role_name}"))
        db.session.commit()

        # Create default admin
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@psfsla.dz")
        if not User.query.filter_by(email=admin_email).first():
            admin_role = Role.query.filter_by(name="admin").first()
            admin = User(
                first_name="Admin",
                last_name="PSFSLA",
                email=admin_email,
                is_active=True,
                is_approved=True,
                email_confirmed=True,
            )
            admin.set_password(os.environ.get("ADMIN_PASSWORD", "Admin@123456"))
            admin.roles.append(admin_role)
            db.session.add(admin)
            db.session.commit()
            print(f"[PSFSLA] Default admin created: {admin_email}")

    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"[PSFSLA] Error seeding data: {e}")