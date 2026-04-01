from __future__ import annotations
from pathlib import Path
from typing import Any
import cv2
from .field_extraction import extract_text_fields
from .image_processing import detect_sheet, extract_bubbles, preprocess_image
from .models import OMRComparisonResult, OMRResult, ScoreSummary
from .processing_config import load_processing_config
from .scoring import compare_answers, evaluate_answers


def process_omr_image(image_path: str | Path, config: dict[str, Any]) -> OMRResult:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    raw = preprocess_image(image)
    aligned = detect_sheet(image, raw["edges"])
    aligned_preprocessed = preprocess_image(aligned)

    question_count, options, bubble_boxes, ocr_regions = load_processing_config(config)
    grouped_bubbles = extract_bubbles(
        aligned_preprocessed["gray"], aligned_preprocessed["thresholded"], options, bubble_boxes
    )
    answers = evaluate_answers(grouped_bubbles, options, question_count=question_count)
    extracted_fields = extract_text_fields(aligned_preprocessed["gray"], ocr_regions)

    return OMRResult(
        answers=answers,
        fields=extracted_fields,
        aligned_shape={
            "width": int(aligned.shape[1]),
            "height": int(aligned.shape[0]),
        },
    )


def evaluate_submission(
    student_image_path: str | Path,
    answer_key_image_path: str | Path,
    config: dict[str, Any],
) -> OMRComparisonResult:
    student_result = process_omr_image(student_image_path, config)
    answer_key_result = process_omr_image(answer_key_image_path, config)

    comparison, score_data = compare_answers(student_result.answers, answer_key_result.answers)
    score_summary = ScoreSummary(**score_data)

    return OMRComparisonResult(
        student=student_result,
        answer_key=answer_key_result,
        score=score_summary,
        comparison=comparison,
    )
