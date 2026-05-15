"""
app/professor/forms.py
-----------------------
WTForms for the professor blueprint.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField,
    IntegerField, BooleanField, URLField, PasswordField,
    DateTimeLocalField, SubmitField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange, URL
from app.models import Category


# ──────────────────────────────────────────────────────────────
#  Course Form
# ──────────────────────────────────────────────────────────────

class CourseForm(FlaskForm):
    """Create / Edit a course (formation)."""

    title_ar = StringField(
        "العنوان بالعربية",
        validators=[DataRequired(message="العنوان بالعربية مطلوب"), Length(max=255)],
        render_kw={"placeholder": "أدخل عنوان التكوين بالعربية", "dir": "rtl"},
    )

    title_fr = StringField(
        "Titre en français",
        validators=[DataRequired(message="Le titre en français est requis"), Length(max=255)],
        render_kw={"placeholder": "Entrez le titre de la formation en français"},
    )

    description = TextAreaField(
        "الوصف",
        validators=[Optional(), Length(max=5000)],
        render_kw={"placeholder": "وصف تفصيلي للتكوين...", "rows": 5, "dir": "rtl"},
    )

    level = SelectField(
        "المستوى",
        choices=[
            ("debutant", "مبتدئ"),
            ("intermediaire", "متوسط"),
            ("avance", "متقدم"),
        ],
        validators=[DataRequired()],
    )

    duration_hours = IntegerField(
        "المدة (بالساعات)",
        validators=[Optional(), NumberRange(min=0, max=9999)],
        render_kw={"placeholder": "مثال: 20"},
    )

    category_id = SelectField(
        "الفئة",
        coerce=int,
        validators=[Optional()],
    )

    thumbnail = FileField(
        "صورة التكوين",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png", "webp"], "الصور فقط (jpg, png, webp)"),
        ],
    )

    is_published = BooleanField("نشر التكوين")
    
    is_free = BooleanField("تكوين مجاني")  # ← أضف هذا
    
    price = IntegerField(  # ← أضف هذا
        "السعر (دج)",
        validators=[Optional(), NumberRange(min=0, max=999999)],
        render_kw={"placeholder": "مثال: 5000"},
    )

    submit = SubmitField("حفظ")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate categories dynamically
        categories = Category.query.order_by(Category.name_ar).all()
        self.category_id.choices = [(0, "— اختر فئة —")] + [
            (c.id, c.name_ar) for c in categories
        ]


# ──────────────────────────────────────────────────────────────
#  Resource Form
# ──────────────────────────────────────────────────────────────

class ResourceForm(FlaskForm):
    """Add a resource (PDF, video, link, slide) to a course."""

    title = StringField(
        "عنوان المورد",
        validators=[DataRequired(message="العنوان مطلوب"), Length(max=255)],
        render_kw={"placeholder": "مثال: الدرس الأول - مقدمة", "dir": "rtl"},
    )

    type = SelectField(
        "نوع المورد",
        choices=[
            ("pdf", "PDF"),
            ("video", "فيديو"),
            ("link", "رابط خارجي"),
            ("slide", "عرض تقديمي"),
        ],
        validators=[DataRequired()],
    )

    url = StringField(
        "الرابط (للموارد الخارجية)",
        validators=[Optional(), Length(max=512)],
        render_kw={"placeholder": "https://..."},
    )

    file = FileField(
        "رفع ملف",
        validators=[
            Optional(),
            FileAllowed(["pdf", "ppt", "pptx", "doc", "docx"], "الملفات المسموحة: pdf, ppt, doc"),
        ],
    )

    description = TextAreaField(
        "وصف",
        validators=[Optional(), Length(max=1000)],
        render_kw={"rows": 3, "dir": "rtl"},
    )

    order = IntegerField(
        "الترتيب",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={"placeholder": "0"},
    )

    is_public = BooleanField("مرئي قبل التسجيل")

    submit = SubmitField("إضافة المورد")


# ──────────────────────────────────────────────────────────────
#  Live Session Form
# ──────────────────────────────────────────────────────────────

class LiveSessionForm(FlaskForm):
    """Schedule a live session."""

    title = StringField(
        "عنوان الجلسة",
        validators=[DataRequired(message="العنوان مطلوب"), Length(max=255)],
        render_kw={"placeholder": "مثال: جلسة مراجعة الوحدة الأولى", "dir": "rtl"},
    )

    description = TextAreaField(
        "وصف الجلسة",
        validators=[Optional(), Length(max=2000)],
        render_kw={"rows": 3, "dir": "rtl"},
    )

    platform = SelectField(
        "المنصة",
        choices=[
            ("zoom", "Zoom"),
            ("teams", "Microsoft Teams"),
            ("google_meet", "Google Meet"),
            ("other", "أخرى"),
        ],
        validators=[DataRequired()],
    )

    meeting_url = StringField(
        "رابط الاجتماع",
        validators=[Optional(), Length(max=512)],
        render_kw={"placeholder": "https://zoom.us/j/..."},
    )

    meeting_id = StringField(
        "معرّف الاجتماع",
        validators=[Optional(), Length(max=128)],
        render_kw={"placeholder": "123 456 7890"},
    )

    password = StringField(
        "كلمة السر (اختياري)",
        validators=[Optional(), Length(max=64)],
    )

    scheduled_at = DateTimeLocalField(
        "تاريخ ووقت الجلسة",
        format="%Y-%m-%dT%H:%M",
        validators=[DataRequired(message="التاريخ والوقت مطلوبان")],
    )

    duration_min = IntegerField(
        "المدة (بالدقائق)",
        validators=[Optional(), NumberRange(min=15, max=480)],
        render_kw={"placeholder": "60"},
    )

    submit = SubmitField("إضافة الجلسة")



# أضف هذا في نهاية الملف

# ──────────────────────────────────────────────────────────────
#  Edit Resource Form (للتعديل)
# ──────────────────────────────────────────────────────────────

class EditResourceForm(FlaskForm):
    """Edit an existing resource."""
    
    title = StringField(
        "عنوان المورد",
        validators=[DataRequired(message="العنوان مطلوب"), Length(max=255)],
    )
    
    type = SelectField(
        "نوع المورد",
        choices=[
            ("pdf", "PDF"),
            ("video", "فيديو"),
            ("link", "رابط خارجي"),
            ("slide", "عرض تقديمي"),
        ],
        validators=[DataRequired()],
    )
    
    url = StringField(
        "الرابط",
        validators=[Optional(), URL(), Length(max=512)],
    )
    
    description = TextAreaField(
        "وصف",
        validators=[Optional(), Length(max=1000)],
    )
    
    order = IntegerField(
        "الترتيب",
        validators=[Optional(), NumberRange(min=0)],
    )
    
    is_public = BooleanField("مرئي قبل التسجيل")
    
    submit = SubmitField("تحديث المورد")


# ──────────────────────────────────────────────────────────────
#  Edit Live Session Form (للتعديل)
# ──────────────────────────────────────────────────────────────

class EditLiveSessionForm(FlaskForm):
    """Edit an existing live session."""
    
    title = StringField(
        "عنوان الجلسة",
        validators=[DataRequired(), Length(max=255)],
    )
    
    description = TextAreaField(
        "وصف الجلسة",
        validators=[Optional(), Length(max=2000)],
    )
    
    platform = SelectField(
        "المنصة",
        choices=[
            ("zoom", "Zoom"),
            ("teams", "Microsoft Teams"),
            ("google_meet", "Google Meet"),
            ("other", "أخرى"),
        ],
        validators=[DataRequired()],
    )
    
    meeting_url = StringField(
        "رابط الاجتماع",
        validators=[Optional(), URL(), Length(max=512)],
    )
    
    meeting_id = StringField(
        "معرّف الاجتماع",
        validators=[Optional(), Length(max=128)],
    )
    
    password = StringField(
        "كلمة السر",
        validators=[Optional(), Length(max=64)],
    )
    
    scheduled_at = DateTimeLocalField(
        "تاريخ ووقت الجلسة",
        format="%Y-%m-%dT%H:%M",
        validators=[DataRequired()],
    )
    
    duration_min = IntegerField(
        "المدة (بالدقائق)",
        validators=[Optional(), NumberRange(min=15, max=480)],
    )
    
    status = SelectField(
        "الحالة",
        choices=[
            ("scheduled", "مجدولة"),
            ("live", "مباشرة الآن"),
            ("ended", "منتهية"),
        ],
        validators=[DataRequired()],
    )
    
    submit = SubmitField("تحديث الجلسة")


# ──────────────────────────────────────────────────────────────
#  Quick Course Filter Form (للفلترة)
# ──────────────────────────────────────────────────────────────

class CourseFilterForm(FlaskForm):
    """Filter courses in professor dashboard."""
    
    status = SelectField(
        "الحالة",
        choices=[
            ("all", "الكل"),
            ("published", "منشور"),
            ("draft", "مسودة"),
        ],
        validators=[Optional()],
    )
    
    category_id = SelectField(
        "الفئة",
        coerce=int,
        validators=[Optional()],
    )
    
    search = StringField(
        "بحث",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "ابحث عن تكوين..."},
    )
    
    submit = SubmitField("تصفية")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import Category
        categories = Category.query.order_by(Category.name_ar).all()
        self.category_id.choices = [(0, "جميع الفئات")] + [(c.id, c.name_ar) for c in categories]