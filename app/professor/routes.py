from flask import Blueprint, render_template
from flask_login import login_required

professor_bp = Blueprint("professor", __name__)

@professor_bp.route("/")
@professor_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("professor/dashboard.html")