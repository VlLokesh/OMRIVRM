from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, render_template, request
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


def _read_submission_files():
    student_file = request.files.get("student_file") or request.files.get("file")
    answer_key_file = request.files.get("answer_key_file") or request.files.get("answer_file")

    if not student_file or student_file.filename == "":
        raise ValueError("Missing `student_file`.")
    if not answer_key_file or answer_key_file.filename == "":
        raise ValueError("Missing `answer_key_file`.")
    if not allowed_file(student_file.filename) or not allowed_file(answer_key_file.filename):
        raise ValueError("Only PNG/JPG/JPEG files are supported.")

    return student_file, answer_key_file


def _score_payload(result) -> dict[str, int | float]:
    return {
        "total_questions": result.score.total_questions,
        "correct": result.score.correct,
        "incorrect": result.score.incorrect,
        "blank": result.score.blank,
        "invalid": result.score.invalid,
        "score_percent": result.score.score_percent,
    }


@omr_blueprint.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@omr_blueprint.route("/health", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok", "message": "OMR service is running."})


@omr_blueprint.route("/evaluate", methods=["POST"])
def evaluate_omr():
    try:
        student_file, answer_key_file = _read_submission_files()
        student_bytes = student_file.read()
        answer_key_bytes = answer_key_file.read()
        result = evaluate_submission(
            student_image_bytes=student_bytes,
            answer_key_image_bytes=answer_key_bytes,
            config=_collect_request_config(),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Processing failed: {exc}"}), 500

    return jsonify(
        {
            "score_summary": _score_payload(result),
            "student_answers": result.student.answers,
            "answer_key_answers": result.answer_key.answers,
            "comparison": result.comparison,
            "fields": result.student.fields,
            "aligned_shape": result.student.aligned_shape,
        }
    ), 200


@omr_blueprint.route("/evaluate/pdf", methods=["POST"])
def evaluate_omr_pdf():
    try:
        student_file, answer_key_file = _read_submission_files()
        student_bytes = student_file.read()
        answer_key_bytes = answer_key_file.read()
        result = evaluate_submission(
            student_image_bytes=student_bytes,
            answer_key_image_bytes=answer_key_bytes,
            config=_collect_request_config(),
        )
        metadata = dict(result.student.fields)
        metadata["Student Image"] = secure_filename(student_file.filename)
        metadata["Answer Key Image"] = secure_filename(answer_key_file.filename)
        pdf_bytes = generate_result_pdf_bytes(
            student_answers=result.student.answers,
            answer_key_answers=result.answer_key.answers,
            comparison=result.comparison,
            score_summary=_score_payload(result),
            metadata=metadata,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Processing failed: {exc}"}), 500

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="evaluator_omr_result.pdf"'
        },
    )
