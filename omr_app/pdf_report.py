from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _render_result_pdf(
    pdf: canvas.Canvas,
    student_answers: dict[str, str],
    answer_key_answers: dict[str, str],
    comparison: dict[str, dict[str, Any]],
    score_summary: dict[str, int | float],
    metadata: dict[str, str] | None = None,
) -> None:
    width, height = A4

    pdf.setTitle("OMR Result")
    left_margin = 32
    right_margin = 32
    top_margin = 40
    bottom_margin = 36
    line_height = 13

    def draw_header(page_number: int) -> float:
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(left_margin, height - top_margin, "OMR Evaluation Report")
        pdf.setFont("Helvetica", 10)
        pdf.drawRightString(width - right_margin, height - top_margin + 2, f"Page {page_number}")

        pdf.drawString(left_margin, height - top_margin - 18, f"Total Questions: {score_summary['total_questions']}")
        pdf.drawString(left_margin + 150, height - top_margin - 18, f"Correct: {score_summary['correct']}")
        pdf.drawString(left_margin + 240, height - top_margin - 18, f"Incorrect: {score_summary['incorrect']}")
        pdf.drawString(left_margin + 350, height - top_margin - 18, f"Blank: {score_summary['blank']}")
        pdf.drawString(left_margin + 430, height - top_margin - 18, f"Invalid: {score_summary['invalid']}")
        pdf.drawString(left_margin, height - top_margin - 34, f"Score: {score_summary['correct']} / {score_summary['total_questions']} ({score_summary['score_percent']}%)")

        current_y = height - top_margin - 50
        if metadata:
            for key, value in metadata.items():
                pdf.drawString(left_margin, current_y, f"{key}: {value or 'N/A'}")
                current_y -= 14

        pdf.setFillColor(colors.HexColor("#dbe7f3"))
        pdf.rect(left_margin, current_y - 6, width - left_margin - right_margin, 18, fill=1, stroke=0)
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left_margin + 6, current_y - 2, "Question")
        pdf.drawString(left_margin + 90, current_y - 2, "Student")
        pdf.drawString(left_margin + 180, current_y - 2, "Answer Key")
        pdf.drawString(left_margin + 300, current_y - 2, "Status")
        return current_y - 20

    rows = list(comparison.items())
    y = draw_header(page_number=1)
    page_number = 1
    pdf.setFont("Helvetica", 10)

    for question, row in rows:
        if y <= bottom_margin:
            pdf.showPage()
            page_number += 1
            y = draw_header(page_number)
            pdf.setFont("Helvetica", 10)

        status = "Correct" if row["is_correct"] else "INCORRECT"
        if row["student"] == "BLANK":
            status = "Blank"
        elif row["student"] == "INVALID":
            status = "Invalid"

        pdf.drawString(left_margin + 6, y, question)
        pdf.drawString(left_margin + 90, y, str(row["student"]))
        pdf.drawString(left_margin + 180, y, str(row["correct_answer"]))
        pdf.drawString(left_margin + 300, y, status)
        y -= line_height

    pdf.save()


def generate_result_pdf(
    output_path: str | Path,
    student_answers: dict[str, str],
    answer_key_answers: dict[str, str],
    comparison: dict[str, dict[str, Any]],
    score_summary: dict[str, int | float],
    metadata: dict[str, str] | None = None,
) -> None:
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    _render_result_pdf(
        pdf=pdf,
        student_answers=student_answers,
        answer_key_answers=answer_key_answers,
        comparison=comparison,
        score_summary=score_summary,
        metadata=metadata,
    )


def generate_result_pdf_bytes(
    student_answers: dict[str, str],
    answer_key_answers: dict[str, str],
    comparison: dict[str, dict[str, Any]],
    score_summary: dict[str, int | float],
    metadata: dict[str, str] | None = None,
) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _render_result_pdf(
        pdf=pdf,
        student_answers=student_answers,
        answer_key_answers=answer_key_answers,
        comparison=comparison,
        score_summary=score_summary,
        metadata=metadata,
    )
    return buffer.getvalue()
