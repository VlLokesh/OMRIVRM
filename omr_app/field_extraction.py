from __future__ import annotations

from typing import Sequence

from .ocr import get_ocr_engine


def extract_text_fields(gray_image, regions: dict[str, Sequence[int]] | None = None) -> dict[str, str]:
    if not regions:
        return {}

    get_ocr_engine()
    extracted: dict[str, str] = {}
    for field_name, box in regions.items():
        x, y, w, h = map(int, box)
        roi = gray_image[y : y + h, x : x + w]
        if roi.size == 0:
            extracted[field_name] = ""
            continue
        try:
            import pytesseract

            text = pytesseract.image_to_string(roi, config="--psm 6")
        except Exception:
            text = ""
        extracted[field_name] = " ".join(text.split())

    return extracted
