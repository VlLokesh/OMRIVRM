# `image_processing.py` Function Guide

This module handles the core image-processing steps for OMR:
1. Normalize perspective of the sheet.
2. Preprocess image into useful representations.
3. Detect the answer sheet region.
4. Detect and group bubbles row-wise for scoring.

## `order_points(points: np.ndarray) -> np.ndarray`
- Input: 4 unordered corner points.
- Output: same 4 points ordered as top-left, top-right, bottom-right, bottom-left.
- How: uses coordinate sum (`x+y`) and difference (`x-y`) heuristics.
- Why: perspective transform requires deterministic corner order.

## `four_point_transform(image: np.ndarray, points: np.ndarray) -> np.ndarray`
- Input: image + 4 sheet corner points.
- Output: perspective-warped, top-down view of the sheet.
- How:
1. Orders corners using `order_points`.
2. Computes max width/height from opposite side lengths.
3. Builds destination rectangle.
4. Uses `cv2.getPerspectiveTransform` + `cv2.warpPerspective`.
- Why: removes camera tilt/skew so bubble positions become consistent.

## `preprocess_image(image: np.ndarray) -> dict[str, np.ndarray]`
- Input: BGR image.
- Output dict:
1. `gray`: grayscale image.
2. `blurred`: Gaussian-blurred grayscale (noise reduction).
3. `thresholded`: binary inverse + Otsu threshold, then morphological open.
4. `edges`: Canny edges from blurred image.
- Why: each downstream step uses a different representation (contours, circles, fill-ratio).

## `detect_sheet(image: np.ndarray, edges: np.ndarray) -> np.ndarray`
- Input: original image + edge map.
- Output: cropped/warped answer sheet image.
- Strategy:
1. Finds external contours sorted by area.
2. Tries to find a 4-point contour; if found, applies `four_point_transform`.
3. Fallback: uses large bounding rectangle if it covers most of the image.
4. Else raises `ValueError`.
- Why: isolates only the answer area before bubble extraction.

## `_bubble_from_box(thresh, box) -> Bubble`
- Internal helper.
- Converts a predefined rectangular bubble box `(x,y,w,h)` into a `Bubble` object.
- Computes `fill_ratio` as non-zero pixels / box area from thresholded image.
- Used when bubble coordinates are predefined (template-driven mode).

## `_bubble_from_circle(thresh, center, radius) -> Bubble`
- Internal helper.
- Builds a circular mask at `(x,y,r)` and computes masked fill ratio.
- Returns a `Bubble` object with synthetic contour/bbox.
- Used when circles are detected via Hough transform (grid mode).

## `_extract_bubbles_predefined(thresholded, bubble_boxes) -> list[Bubble]`
- Internal helper.
- Maps each predefined box to a `Bubble` using `_bubble_from_box`.
- Use case: known fixed OMR layout coordinates.

## `_cluster_axis(values, max_gap, min_cluster_size) -> list[int]`
- Internal helper.
- Clusters sorted coordinates into groups where neighbor distance <= `max_gap`.
- Returns cluster centers (mean per cluster) if cluster size is large enough.
- Why: stabilizes noisy circle detections into clean X/Y grid lines.

## `_extract_bubbles_hough_grid(gray_image, thresholded, options) -> list[list[Bubble]] | None`
- Internal helper.
- Attempts circle-based extraction with `cv2.HoughCircles`.
- Workflow:
1. Detect circles.
2. Cluster X and Y centers.
3. Validate enough columns/rows and column count divisible by option count.
4. Build grouped bubbles row-by-row in option blocks.
- Returns:
1. grouped bubble rows if successful.
2. `None` if grid constraints fail.
- Why: preferred path when bubbles are circular and detection is clean.

## `_extract_bubbles_contours(thresholded) -> list[Bubble]`
- Internal helper.
- Contour-based fallback extraction.
- Filters candidates by:
1. minimum contour area and bbox size.
2. near-square aspect ratio.
3. non-empty ROI.
- Computes fill ratio for each candidate and sorts top-to-bottom then left-to-right.
- Raises `ValueError` if none found.

## `extract_bubbles(gray_image, thresholded, options, bubble_boxes=None) -> list[list[Bubble]]`
- Public bubble extraction entry point.
- Decision order:
1. If `bubble_boxes` provided: use predefined extraction.
2. Else try Hough-grid extraction.
3. If Hough fails, use contour fallback.
- Then groups flat bubbles into rows using adaptive `row_tolerance` based on median bubble height.
- Returns row-wise groups, each row sorted by X coordinate.
- Why: robust across template-driven, ideal-circle, and noisy contour scenarios.

## End-to-End Role In Pipeline
- This module does not score answers directly.
- It prepares normalized sheet images and bubble groups with `fill_ratio`, which later logic can interpret as marked/unmarked options and compute final scores.
