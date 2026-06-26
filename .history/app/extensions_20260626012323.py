from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail

# تأكد من تعيين session_options لإغلاق الجلسة تلقائياً
db = SQLAlchemy(session_options={"autoflush": False, "expire_on_commit": False})

login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

login_manager.login_view = "auth.login"
login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى هذه الصفحة"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))