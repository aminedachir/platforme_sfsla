from flask import Blueprint, render_template
from app.models import Course, Category

courses_bp = Blueprint("courses", __name__)

@courses_bp.route("/")
def list():
    courses = Course.query.filter_by(is_published=True).all()
    categories = Category.query.order_by(Category.order).all()
    return render_template("courses/list.html", courses=courses, categories=categories)

@courses_bp.route("/<int:course_id>")
def detail(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template("courses/detail.html", course=course)
