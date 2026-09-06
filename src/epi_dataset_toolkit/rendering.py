"""Drawing boxes onto an image. Knows nothing about files or label formats."""

from collections.abc import Sequence

import cv2
import numpy as np

from .boxes import Box
from .palette import Color

_FONT = cv2.FONT_HERSHEY_SIMPLEX


def class_label(class_id: int, class_names: Sequence[str]) -> str:
    """Name for a class id, degrading gracefully when the id is out of range."""
    if 0 <= class_id < len(class_names):
        return class_names[class_id]
    return f"class_{class_id}"


def draw_boxes(
    image: np.ndarray,
    boxes: Sequence[Box],
    class_names: Sequence[str],
    palette: Sequence[Color],
    thickness: int = 2,
    font_scale: float | None = None,
) -> np.ndarray:
    """Return a copy of `image` with every box drawn and labeled.

    Takes boxes and colors as arguments rather than reading them from disk or
    from a module-level constant, so the same function serves the visualizer
    today and the validator's debug output later.
    """
    canvas = image.copy()
    height, width = canvas.shape[:2]

    if font_scale is None:
        # Keep the text legible whether the image is 640px or 4K.
        font_scale = max(0.4, min(width, height) / 1280)

    for box in boxes:
        x1, y1, x2, y2 = box.to_corners(width, height)
        color = palette[box.class_id % len(palette)] if palette else (0, 255, 0)

        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)
        _draw_label(canvas, class_label(box.class_id, class_names), x1, y1, color, font_scale)

    return canvas


def _draw_label(
    canvas: np.ndarray, text: str, x: int, y: int, color: Color, font_scale: float
) -> None:
    """Draw `text` on a filled tag above the box, kept inside the image."""
    height, width = canvas.shape[:2]
    (text_w, text_h), baseline = cv2.getTextSize(text, _FONT, font_scale, 1)

    top = y - text_h - baseline
    if top < 0:
        # The box touches the top edge, so the tag goes inside it instead.
        top = y
    top = max(0, min(top, height - text_h - baseline))
    left = max(0, min(x, width - text_w))

    cv2.rectangle(
        canvas, (left, top), (left + text_w, top + text_h + baseline), color, cv2.FILLED
    )
    cv2.putText(
        canvas, text, (left, top + text_h), _FONT, font_scale, (0, 0, 0), 1, cv2.LINE_AA
    )
