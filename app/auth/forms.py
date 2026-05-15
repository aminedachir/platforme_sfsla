"""
app/auth/forms.py
-----------------
WTForms for login, registration, and password reset.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User


class LoginForm(FlaskForm):
    email    = StringField("البريد الإلكتروني", validators=[DataRequired(), Email()])
    password = PasswordField("كلمة المرور",     validators=[DataRequired()])
    remember = BooleanField("تذكرني")
    submit   = SubmitField("تسجيل الدخول")


class RegisterForm(FlaskForm):
    first_name = StringField("الاسم",   validators=[DataRequired(), Length(2, 64)])
    last_name  = StringField("اللقب",   validators=[DataRequired(), Length(2, 64)])
    email      = StringField("البريد الإلكتروني", validators=[DataRequired(), Email()])
    phone      = StringField("رقم الهاتف (اختياري)")
    wilaya     = SelectField("الولاية",  choices=[], coerce=str)
    role       = SelectField("نوع الحساب",
                             choices=[("student", "طالب تكوين"), ("professor", "أستاذ / مكوّن")])
    password   = PasswordField("كلمة المرور",
                               validators=[DataRequired(), Length(8, 128,
                               message="كلمة المرور يجب أن تكون 8 أحرف على الأقل")])
    confirm    = PasswordField("تأكيد كلمة المرور",
                               validators=[DataRequired(), EqualTo("password",
                               message="كلمتا المرور غير متطابقتان")])
    terms      = BooleanField("أوافق على شروط الاستخدام", validators=[DataRequired()])
    submit     = SubmitField("إنشاء حساب")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("هذا البريد الإلكتروني مسجل مسبقاً.")


class ForgotPasswordForm(FlaskForm):
    email  = StringField("البريد الإلكتروني", validators=[DataRequired(), Email()])
    submit = SubmitField("إرسال رابط الاستعادة")


WILAYAS = [
    ("", "اختر الولاية"),
    ("01", "01 - أدرار"),("02", "02 - الشلف"),("03", "03 - الأغواط"),
    ("04", "04 - أم البواقي"),("05", "05 - باتنة"),("06", "06 - بجاية"),
    ("07", "07 - بسكرة"),("08", "08 - بشار"),("09", "09 - البليدة"),
    ("10", "10 - البويرة"),("11", "11 - تمنراست"),("12", "12 - تبسة"),
    ("13", "13 - تلمسان"),("14", "14 - تيارت"),("15", "15 - تيزي وزو"),
    ("16", "16 - الجزائر"),("17", "17 - الجلفة"),("18", "18 - جيجل"),
    ("19", "19 - سطيف"),("20", "20 - سعيدة"),("21", "21 - سكيكدة"),
    ("22", "22 - سيدي بلعباس"),("23", "23 - عنابة"),("24", "24 - قالمة"),
    ("25", "25 - قسنطينة"),("26", "26 - المدية"),("27", "27 - مستغانم"),
    ("28", "28 - المسيلة"),("29", "29 - معسكر"),("30", "30 - ورقلة"),
    ("31", "31 - وهران"),("32", "32 - البيض"),("33", "33 - إليزي"),
    ("34", "34 - برج بوعريريج"),("35", "35 - بومرداس"),("36", "36 - الطارف"),
    ("37", "37 - تندوف"),("38", "38 - تيسمسيلت"),("39", "39 - الوادي"),
    ("40", "40 - خنشلة"),("41", "41 - سوق أهراس"),("42", "42 - تيبازة"),
    ("43", "43 - ميلة"),("44", "44 - عين الدفلى"),("45", "45 - النعامة"),
    ("46", "46 - عين تيموشنت"),("47", "47 - غرداية"),("48", "48 - غليزان"),
    ("49", "49 - المغير"),("50", "50 - المنيعة"),("51", "51 - أولاد جلال"),
    ("52", "52 - برج باجي مختار"),("53", "53 - بني عباس"),("54", "54 - تيميمون"),
    ("55", "55 - تقرت"),("56", "56 - جانت"),("57", "57 - عين صالح"),
    ("58", "58 - عين قزام"),
]
