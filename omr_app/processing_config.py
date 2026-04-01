from __future__ import annotations

import json
from typing import Any

from .config import DEFAULT_OPTIONS, DEFAULT_QUESTIONS


def coerce_json_value(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return value
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value
    return value


def load_processing_config(payload: dict[str, Any]) -> tuple[int, tuple[str, ...], list[list[int]] | None, dict[str, list[int]] | None]:
    if "config" in payload:
        config_value = coerce_json_value(payload["config"])
        if isinstance(config_value, dict):
            merged = dict(payload)
            merged.update(config_value)
            payload = merged

    question_count = int(payload.get("question_count", DEFAULT_QUESTIONS))
    options_value = coerce_json_value(payload.get("options", DEFAULT_OPTIONS))
    if isinstance(options_value, str):
        options = tuple(part.strip() for part in options_value.split(",") if part.strip())
    else:
        options = tuple(options_value)

    if not options:
        raise ValueError("At least one option label is required.")

    bubble_boxes = coerce_json_value(payload.get("bubble_boxes"))
    ocr_regions = coerce_json_value(payload.get("ocr_regions"))
    return question_count, options, bubble_boxes, ocr_regions
