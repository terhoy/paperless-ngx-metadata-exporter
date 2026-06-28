from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .config import AppConfig
from .routes.ui import ui_bp
from .routes.api import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    cfg = AppConfig.from_env()
    app.config["APP_CONFIG"] = cfg
    app.secret_key = cfg.secret_key

    Limiter(
        get_remote_address,
        app=app,
        default_limits=["300 per minute"],
        storage_uri="memory://",
    )

    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app
