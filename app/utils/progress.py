"""
app/utils/progress.py
----------------------
نظام حساب تقدم الطالب التلقائي بناءً على الموارد المكتملة والجلسات المحضورة.

الأوزان حسب نوع المورد:
  pdf    → 15%
  video  → 20%
  link   →  5%
  slide  → 10%   (نفس فئة "other" – وزن خفيف)
  other  → 10%

  حضور جلسة مباشرة → 25% (موزّعة على عدد الجلسات)

ملاحظة: المجموع النهائي يُطبَّع إلى 100% دائماً.
"""

from __future__ import annotations
from app.extensions import db
from app.models import Course, Resource, LiveSession, CompletedResource, AttendedSession


# ── أوزان نوع المورد (نقاط خام لكل عنصر) ──────────────────────
RESOURCE_WEIGHTS: dict[str, float] = {
    "pdf":   15.0,
    "video": 20.0,
    "link":   5.0,
    "slide": 10.0,
}
DEFAULT_RESOURCE_WEIGHT = 10.0   # لأي نوع غير محدد

SESSION_WEIGHT = 25.0            # نقاط لكل جلسة مباشرة


def _resource_weight(res_type: str) -> float:
    return RESOURCE_WEIGHTS.get(res_type, DEFAULT_RESOURCE_WEIGHT)


def calculate_progress(student_id: int, course_id: int) -> float:
    """
    تحسب النسبة المئوية للتقدم لطالب في مساق معين.

    الخوارزمية:
    1. تجمع النقاط القصوى الممكنة (كل الموارد + كل الجلسات).
    2. تجمع النقاط المكتسبة (الموارد المكتملة + الجلسات المحضورة).
    3. تقسّم وتُعيد نسبة من 0.0 إلى 100.0.

    إذا كان المساق فارغاً (لا موارد ولا جلسات) → تُعيد 0.0.
    """
    # ── جلب بيانات المساق ─────────────────────────────────────
    resources: list[Resource] = (
        Resource.query.filter_by(course_id=course_id).all()
    )
    sessions: list[LiveSession] = (
        LiveSession.query.filter_by(course_id=course_id).all()
    )

    # ── حساب النقاط القصوى ────────────────────────────────────
    max_points: float = sum(_resource_weight(r.type) for r in resources)
    max_points += SESSION_WEIGHT * len(sessions)

    if max_points == 0:
        return 0.0

    # ── الموارد المكتملة من قِبَل الطالب ──────────────────────
    completed_ids: set[int] = {
        cr.resource_id
        for cr in CompletedResource.query.filter_by(
            student_id=student_id, course_id=course_id
        ).all()
    }

    earned_points: float = sum(
        _resource_weight(r.type)
        for r in resources
        if r.id in completed_ids
    )

    # ── الجلسات المحضورة ──────────────────────────────────────
    attended_ids: set[int] = {
        a.session_id
        for a in AttendedSession.query.filter_by(
            student_id=student_id, course_id=course_id
        ).all()
    }

    earned_points += SESSION_WEIGHT * sum(
        1 for s in sessions if s.id in attended_ids
    )

    # ── حساب النسبة المئوية وتطبيعها ─────────────────────────
    progress = min(100.0, (earned_points / max_points) * 100.0)
    return round(progress, 2)


def sync_enrollment_progress(student_id: int, course_id: int) -> float:
    """
    تحسب التقدم وتحدّث حقل Enrollment.progress في قاعدة البيانات.
    تُعيد القيمة الجديدة للتقدم.

    استخدم هذه الدالة بعد كل إكمال مورد أو تسجيل حضور.
    """
    from app.models import Enrollment

    enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        course_id=course_id,
    ).first()

    if enrollment is None:
        return 0.0

    new_progress = calculate_progress(student_id, course_id)
    enrollment.progress = new_progress
    # لا نستدعي commit() هنا — المسؤولية على المُستدعي
    return new_progress