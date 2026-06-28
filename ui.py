from flask import Blueprint, current_app, render_template

from ..config import APP_VERSION
from ..security import requires_auth

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/")
@requires_auth
def index():
    cfg = current_app.config["APP_CONFIG"]
    return render_template("index.html", default_language=cfg.default_language, app_version=APP_VERSION)
