from __future__ import annotations

import base64
import os
import uuid
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request
from werkzeug.utils import secure_filename

from .config import ALLOWED_EXTENSIONS
from .pdf_report import generate_result_pdf_bytes
from .service import evaluate_submission

omr_blueprint = Blueprint("omr", __name__)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _collect_request_config() -> dict[str, Any]:
    config = request.form.to_dict(flat=True)
    if request.is_json:
        config.update(request.get_json(silent=True) or {})
    return config


def _save_upload(file_storage, destination_folder: str) -> str:
    filename = f"{uuid.uuid4().hex}_{secure_filename(file_storage.filename)}"
    file_path = os.path.join(destination_folder, filename)
    file_storage.save(file_path)
    return file_path


def _delete_file_if_exists(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


@omr_blueprint.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@omr_blueprint.route("/health", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok", "message": "OMR service is running."})


@omr_blueprint.route("/evaluate", methods=["POST"])
def evaluate_omr():
    student_file = request.files.get("student_file") or request.files.get("file")
    answer_key_file = request.files.get("answer_key_file") or request.files.get("answer_file")

    if not student_file or student_file.filename == "":
        return jsonify({"error": "Missing `student_file`."}), 400
    if not answer_key_file or answer_key_file.filename == "":
        return jsonify({"error": "Missing `answer_key_file`."}), 400
    if not allowed_file(student_file.filename) or not allowed_file(answer_key_file.filename):
        return jsonify({"error": "Only PNG/JPG/JPEG files are supported."}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    student_path = _save_upload(student_file, upload_folder)
    answer_key_path = _save_upload(answer_key_file, upload_folder)

    try:
        result = evaluate_submission(
            student_image_path=student_path,
            answer_key_image_path=answer_key_path,
            config=_collect_request_config(),
        )
        pdf_filename = f"{uuid.uuid4().hex}_omr_result.pdf"
        metadata = dict(result.student.fields)
        metadata["Student Image"] = secure_filename(student_file.filename)
        metadata["Answer Key Image"] = secure_filename(answer_key_file.filename)
        pdf_bytes = generate_result_pdf_bytes(
            student_answers=result.student.answers,
            answer_key_answers=result.answer_key.answers,
            comparison=result.comparison,
            score_summary={
                "total_questions": result.score.total_questions,
                "correct": result.score.correct,
                "incorrect": result.score.incorrect,
                "blank": result.score.blank,
                "invalid": result.score.invalid,
                "score_percent": result.score.score_percent,
            },
            metadata=metadata,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Processing failed: {exc}"}), 500
    finally:
        _delete_file_if_exists(student_path)
        _delete_file_if_exists(answer_key_path)

    return jsonify(
        {
            "score_summary": {
                "total_questions": result.score.total_questions,
                "correct": result.score.correct,
                "incorrect": result.score.incorrect,
                "blank": result.score.blank,
                "invalid": result.score.invalid,
                "score_percent": result.score.score_percent,
            },
            "student_answers": result.student.answers,
            "answer_key_answers": result.answer_key.answers,
            "comparison": result.comparison,
            "fields": result.student.fields,
            "aligned_shape": result.student.aligned_shape,
            "pdf_filename": pdf_filename,
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        }
    ), 200
