from __future__ import annotations

from flask import Flask

from .config import MAX_UPLOAD_SIZE
from .routes import omr_blueprint


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
    app.register_blueprint(omr_blueprint)
    return app
