from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .config import MAX_UPLOAD_SIZE
from .routes import omr_blueprint


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
    CORS(
        app,
        resources={
            r"/health": {"origins": "*"},
            r"/evaluate*": {"origins": "*"},
        },
    )
    app.register_blueprint(omr_blueprint)
    return app
