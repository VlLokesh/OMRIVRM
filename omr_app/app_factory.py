from __future__ import annotations

from pathlib import Path

from flask import Flask

from .config import MAX_UPLOAD_SIZE, UPLOAD_DIR
from .ocr import init_tesseract
from .routes import omr_blueprint


def create_app() -> Flask:
    init_tesseract()
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
    app.register_blueprint(omr_blueprint)
    return app
