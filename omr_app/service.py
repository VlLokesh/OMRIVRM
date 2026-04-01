from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .field_extraction import extract_text_fields
from .image_processing import detect_sheet, extract_bubbles, preprocess_image
from .models import OMRComparisonResult, OMRResult, ScoreSummary
from .processing_config import load_processing_config
from .scoring import compare_answers, evaluate_answers


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    image_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode uploaded image.")
    return image


def process_omr_image(image: np.ndarray, config: dict[str, Any]) -> OMRResult:
    if image is None or image.size == 0:
        raise ValueError("Uploaded image is empty.")

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
    student_image_bytes: bytes,
    answer_key_image_bytes: bytes,
    config: dict[str, Any],
) -> OMRComparisonResult:
    student_result = process_omr_image(decode_image_bytes(student_image_bytes), config)
    answer_key_result = process_omr_image(decode_image_bytes(answer_key_image_bytes), config)

    comparison, score_data = compare_answers(student_result.answers, answer_key_result.answers)
    score_summary = ScoreSummary(**score_data)

    return OMRComparisonResult(
        student=student_result,
        answer_key=answer_key_result,
        score=score_summary,
        comparison=comparison,
    )
