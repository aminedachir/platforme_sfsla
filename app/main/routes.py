from flask import Blueprint, render_template
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
    return render_template("main/about.html")

@main_bp.route("/contact")
def contact():
    return render_template("main/contact.html")
