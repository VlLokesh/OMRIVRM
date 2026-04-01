from __future__ import annotations

from typing import Sequence

import numpy as np


def evaluate_answers(
    grouped_bubbles: Sequence[Sequence],
    options: Sequence[str],
    mark_threshold: float = 0.20,
    ambiguity_margin: float = 0.06,
    question_count: int | None = None,
) -> dict[str, str]:
    answers: dict[str, str] = {}
    total_questions = question_count or len(grouped_bubbles)

    for index in range(total_questions):
        label = f"Q{index + 1}"
        if index >= len(grouped_bubbles):
            answers[label] = "BLANK"
            continue

        row = list(grouped_bubbles[index])[: len(options)]
        if len(row) < len(options):
            answers[label] = "BLANK"
            continue

        scores = [bubble.fill_ratio for bubble in row]
        max_score = max(scores)
        marked_indices = [i for i, score in enumerate(scores) if score >= mark_threshold]
        if not marked_indices:
            answers[label] = "BLANK"
            continue

        strong_indices = [
            i for i, score in enumerate(scores) if max_score - score <= ambiguity_margin
        ]
        if len(strong_indices) > 1 and max_score >= mark_threshold:
            answers[label] = "INVALID"
            continue

        best_index = int(np.argmax(scores))
        answers[label] = options[best_index]

    return answers


def compare_answers(student_answers: dict[str, str], answer_key_answers: dict[str, str]) -> tuple[dict[str, dict[str, str | bool]], dict[str, int | float]]:
    question_labels = sorted(answer_key_answers.keys(), key=lambda label: int(label[1:]))
    comparison: dict[str, dict[str, str | bool]] = {}

    correct = 0
    incorrect = 0
    blank = 0
    invalid = 0

    for question in question_labels:
        student_answer = student_answers.get(question, "BLANK")
        key_answer = answer_key_answers.get(question, "BLANK")
        is_blank = student_answer == "BLANK"
        is_invalid = student_answer == "INVALID"
        is_correct = student_answer == key_answer and not is_blank and not is_invalid

        if is_correct:
            correct += 1
        elif is_blank:
            blank += 1
        elif is_invalid:
            invalid += 1
        else:
            incorrect += 1

        comparison[question] = {
            "student": student_answer,
            "correct_answer": key_answer,
            "is_correct": is_correct,
        }

    total = len(question_labels)
    score_percent = round((correct / total) * 100, 2) if total else 0.0
    summary = {
        "total_questions": total,
        "correct": correct,
        "incorrect": incorrect,
        "blank": blank,
        "invalid": invalid,
        "score_percent": score_percent,
    }
    return comparison, summary
