from __future__ import annotations

import os
from typing import Any


def init_tesseract() -> None:
    path = os.environ.get("TESSERACT_CMD")
    if not path:
        return

    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = path
    except Exception:
        pass


ocr_engine: Any = None


def get_ocr_engine() -> Any:
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = "tesseract"
    return ocr_engine
