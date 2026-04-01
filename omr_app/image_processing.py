from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

from .models import Bubble


def order_points(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = points.sum(axis=1)
    diff = np.diff(points, axis=1)
    rect[0] = points[np.argmin(s)]
    rect[2] = points[np.argmax(s)]
    rect[1] = points[np.argmin(diff)]
    rect[3] = points[np.argmax(diff)]
    return rect


def four_point_transform(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    rect = order_points(points)
    tl, tr, br, bl = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)

    max_width = max(int(width_a), int(width_b))
    max_height = max(int(height_a), int(height_b))

    destination = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )

    matrix = cv2.getPerspectiveTransform(rect, destination)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def preprocess_image(image: np.ndarray) -> dict[str, np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresholded = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )[1]
    opened = cv2.morphologyEx(
        thresholded,
        cv2.MORPH_OPEN,
        np.ones((3, 3), dtype=np.uint8),
        iterations=1,
    )
    edges = cv2.Canny(blurred, 75, 200)
    return {
        "gray": gray,
        "blurred": blurred,
        "thresholded": opened,
        "edges": edges,
    }


def detect_sheet(image: np.ndarray, edges: np.ndarray) -> np.ndarray:
    contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approximation) == 4:
            return four_point_transform(image, approximation.reshape(4, 2))

    if contours:
        x, y, w, h = cv2.boundingRect(contours[0])
        if w > image.shape[1] * 0.6 and h > image.shape[0] * 0.6:
            return image[y : y + h, x : x + w]

    raise ValueError("Unable to detect answer sheet contour.")


def _bubble_from_box(thresh: np.ndarray, box: tuple[int, int, int, int]) -> Bubble:
    x, y, w, h = box
    roi = thresh[y : y + h, x : x + w]
    area = max(w * h, 1)
    fill_ratio = float(cv2.countNonZero(roi)) / float(area)
    return Bubble(
        contour=np.array(
            [[[x, y]], [[x + w, y]], [[x + w, y + h]], [[x, y + h]]], dtype=np.int32
        ),
        bbox=box,
        center=(x + w // 2, y + h // 2),
        fill_ratio=fill_ratio,
    )


def _bubble_from_circle(thresh: np.ndarray, center: tuple[int, int], radius: int) -> Bubble:
    x, y = center
    mask = np.zeros(thresh.shape, dtype=np.uint8)
    cv2.circle(mask, (x, y), max(radius, 2), 255, -1)
    roi = cv2.bitwise_and(thresh, thresh, mask=mask)
    masked_area = max(cv2.countNonZero(mask), 1)
    fill_ratio = float(cv2.countNonZero(roi)) / float(masked_area)
    diameter = radius * 2
    return Bubble(
        contour=np.array([[[x, y]]], dtype=np.int32),
        bbox=(x - radius, y - radius, diameter, diameter),
        center=center,
        fill_ratio=fill_ratio,
    )


def _extract_bubbles_predefined(
    thresholded: np.ndarray, bubble_boxes: Sequence[Sequence[int]]
) -> list[Bubble]:
    return [_bubble_from_box(thresholded, tuple(map(int, box))) for box in bubble_boxes]


def _cluster_axis(values: np.ndarray, max_gap: int, min_cluster_size: int) -> list[int]:
    if values.size == 0:
        return []

    sorted_values = np.sort(values.astype(int))
    clusters: list[list[int]] = [[int(sorted_values[0])]]
    for value in sorted_values[1:]:
        if abs(int(value) - clusters[-1][-1]) <= max_gap:
            clusters[-1].append(int(value))
        else:
            clusters.append([int(value)])

    return [
        int(round(sum(cluster) / len(cluster)))
        for cluster in clusters
        if len(cluster) >= min_cluster_size
    ]


def _extract_bubbles_hough_grid(
    gray_image: np.ndarray, thresholded: np.ndarray, options: Sequence[str]
) -> list[list[Bubble]] | None:
    circles = cv2.HoughCircles(
        gray_image,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=18,
        param1=60,
        param2=14,
        minRadius=7,
        maxRadius=10,
    )
    if circles is None:
        return None

    detected = np.round(circles[0]).astype(int)
    x_centers = _cluster_axis(detected[:, 0], max_gap=8, min_cluster_size=20)
    y_centers = _cluster_axis(detected[:, 1], max_gap=8, min_cluster_size=18)

    if len(x_centers) < len(options) or len(y_centers) < 5:
        return None
    if len(x_centers) % len(options) != 0:
        return None

    radius = max(3, int(round(float(np.median(detected[:, 2])) * 0.7)))
    grouped: list[list[Bubble]] = []
    for block_start in range(0, len(x_centers), len(options)):
        option_x_positions = x_centers[block_start : block_start + len(options)]
        for y in y_centers:
            grouped.append([
                _bubble_from_circle(thresholded, (x, y), radius)
                for x in option_x_positions
            ])

    return grouped


def _extract_bubbles_contours(thresholded: np.ndarray) -> list[Bubble]:
    contours, _ = cv2.findContours(
        thresholded.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    bubbles: list[Bubble] = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / float(h) if h else 0
        area = cv2.contourArea(contour)

        if area < 150 or w < 12 or h < 12:
            continue
        if not 0.75 <= aspect_ratio <= 1.25:
            continue

        roi = thresholded[y : y + h, x : x + w]
        if roi.size == 0:
            continue

        fill_ratio = float(cv2.countNonZero(roi)) / float(w * h)
        bubbles.append(
            Bubble(
                contour=contour,
                bbox=(x, y, w, h),
                center=(x + w // 2, y + h // 2),
                fill_ratio=fill_ratio,
            )
        )

    if not bubbles:
        raise ValueError("No bubble candidates detected.")

    return sorted(bubbles, key=lambda bubble: (bubble.center[1], bubble.center[0]))


def extract_bubbles(
    gray_image: np.ndarray,
    thresholded: np.ndarray,
    options: Sequence[str],
    bubble_boxes: Sequence[Sequence[int]] | None = None,
) -> list[list[Bubble]]:
    if bubble_boxes:
        bubbles = _extract_bubbles_predefined(thresholded, bubble_boxes)
    else:
        hough_grouped = _extract_bubbles_hough_grid(gray_image, thresholded, options)
        if hough_grouped:
            return hough_grouped
        bubbles = _extract_bubbles_contours(thresholded)

    row_tolerance = max(12, int(np.median([bubble.bbox[3] for bubble in bubbles]) * 0.8))
    rows: list[list[Bubble]] = []

    for bubble in bubbles:
        if not rows:
            rows.append([bubble])
            continue

        last_row_y = int(np.mean([candidate.center[1] for candidate in rows[-1]]))
        if abs(bubble.center[1] - last_row_y) <= row_tolerance:
            rows[-1].append(bubble)
        else:
            rows.append([bubble])

    return [sorted(row, key=lambda bubble: bubble.center[0]) for row in rows]
