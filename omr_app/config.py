import sys
from pathlib import Path
from typing import Final

ALLOWED_EXTENSIONS: Final[set[str]] = {"png", "jpg", "jpeg"}
DEFAULT_QUESTIONS: Final[int] = 150
DEFAULT_OPTIONS: Final[tuple[str, ...]] = ("A", "B", "C", "D")
MAX_UPLOAD_SIZE: Final[int] = 10 * 1024 * 1024

APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)).resolve()
