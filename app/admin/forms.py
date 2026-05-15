"""
app/admin/forms.py
------------------
Admin Panel — WTForms definitions
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, IntegerField, SelectField,
    BooleanField, HiddenField
)
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from app.models import Category


class CategoryForm(FlaskForm):
    name_ar     = StringField(
        "الاسم بالعربية",
        validators=[DataRequired(message="الاسم بالعربية مطلوب"), Length(max=128)],
        render_kw={"placeholder": "مثال: تقنية المعلومات", "dir": "rtl"},
    )
    name_fr     = StringField(
        "Nom en français",
        validators=[DataRequired(message="Le nom en français est requis"), Length(max=128)],
        render_kw={"placeholder": "ex: Technologies de l'information"},
    )
    slug        = StringField(
        "Slug (URL)",
        validators=[DataRequired(message="الـ slug مطلوب"), Length(max=128)],
        render_kw={"placeholder": "tech-information", "dir": "ltr"},
    )
    description = TextAreaField(
        "الوصف",
        validators=[Optional()],
        render_kw={"rows": 3, "placeholder": "وصف مختصر للتصنيف..."},
    )
    icon        = StringField(
        "Bootstrap Icon",
        validators=[Optional(), Length(max=64)],
        render_kw={"placeholder": "bi-book", "dir": "ltr"},
    )
    color       = StringField(
        "اللون (HEX)",
        validators=[Optional(), Length(max=16)],
        render_kw={"placeholder": "#1B2A52", "dir": "ltr", "type": "color"},
    )
    order       = IntegerField(
        "الترتيب",
        validators=[Optional()],
        default=0,
        render_kw={"placeholder": "0"},
    )

    def validate_slug(self, field):
        # Check uniqueness — allow same slug when editing (handled in route via obj)
        existing = Category.query.filter_by(slug=field.data).first()
        if existing:
            # If we're in edit mode the route passes obj=cat so the id will differ
            # We rely on the route to skip this form validation for same-object edits
            # Simple approach: only raise if another category has this slug
            raise ValidationError("هذا الـ slug مستخدم بالفعل.")


class UserFilterForm(FlaskForm):
    """Used for GET-based filtering (no CSRF needed)."""
    class Meta:
        csrf = False

    q      = StringField("البحث", validators=[Optional()],
                         render_kw={"placeholder": "الاسم أو البريد..."})
    role   = SelectField(
        "الدور",
        choices=[("", "الكل"), ("student", "طالب"), ("professor", "أستاذ"), ("admin", "مسؤول")],
        validators=[Optional()],
    )
    status = SelectField(
        "الحالة",
        choices=[
            ("", "الكل"),
            ("active", "نشط"),
            ("inactive", "معطّل"),
            ("pending", "بانتظار الموافقة"),
        ],
        validators=[Optional()],
    )