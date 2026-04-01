from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class Bubble:
    contour: np.ndarray
    bbox: tuple[int, int, int, int]
    center: tuple[int, int]
    fill_ratio: float


@dataclass
class ScoreSummary:
    total_questions: int
    correct: int
    incorrect: int
    blank: int
    invalid: int
    score_percent: float


@dataclass
class OMRResult:
    answers: dict[str, str]
    fields: dict[str, str]
    aligned_shape: dict[str, int]


@dataclass
class OMRComparisonResult:
    student: OMRResult
    answer_key: OMRResult
    score: ScoreSummary
    comparison: dict[str, dict[str, Any]]
