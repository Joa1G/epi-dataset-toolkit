"""Drawing boxes onto an image. Knows nothing about files or label formats."""

from collections.abc import Iterable, Sequence

import cv2
import numpy as np

from .boxes import Box
from .palette import Color

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_PAD = 3

# A tag narrower than this stops being readable no matter how small its box is,
# so past this point the tag stays big and the placement logic deals with it.
_MIN_SCALE_RATIO = 0.5

Rect = tuple[int, int, int, int]


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
    legend: bool = True,
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

    drawn = []
    for box in boxes:
        corners = box.to_corners(width, height)
        color = palette[box.class_id % len(palette)] if palette else (0, 255, 0)
        cv2.rectangle(canvas, corners[:2], corners[2:], color, thickness)
        drawn.append((box, corners, color))

    # Every rectangle is on the canvas before the first tag, so no outline can
    # be drawn over a tag that was already placed.
    occupied: list[Rect] = []
    if legend and drawn:
        occupied.append(
            _draw_legend(canvas, {box.class_id for box, _, _ in drawn}, class_names, palette, font_scale)
        )

    # Biggest boxes first: in a crowd, the object that dominates the frame is
    # the one worth naming, and it claims its spot before the small ones.
    for box, corners, color in sorted(drawn, key=lambda item: item[0].area, reverse=True):
        _draw_label(canvas, class_label(box.class_id, class_names), corners, color, font_scale, occupied)

    return canvas


def _draw_label(
    canvas: np.ndarray,
    text: str,
    corners: Rect,
    color: Color,
    base_scale: float,
    occupied: list[Rect],
) -> None:
    """Draw `text` on a filled tag by its box, avoiding tags already placed."""
    height, width = canvas.shape[:2]
    x1, y1, _, y2 = corners
    box_width = max(1, corners[2] - x1)

    # A tag wider than its own box points at the wrong object once boxes crowd
    # together, so shrink it to fit - down to the readability floor.
    scale = base_scale
    (text_w, text_h), baseline = cv2.getTextSize(text, _FONT, scale, 1)
    if text_w > box_width:
        scale = max(base_scale * _MIN_SCALE_RATIO, base_scale * box_width / text_w)
        (text_w, text_h), baseline = cv2.getTextSize(text, _FONT, scale, 1)

    tag_w = text_w + 2 * _PAD
    tag_h = text_h + baseline + 2 * _PAD
    left = max(0, min(x1, width - tag_w))

    for top in (y1 - tag_h, y1, y2 - tag_h, y2):
        if top < 0 or top + tag_h > height:
            continue
        tag = (left, top, left + tag_w, top + tag_h)
        if any(_overlaps(tag, other) for other in occupied):
            continue
        _fill_tag(canvas, tag, text, color, scale, text_h)
        occupied.append(tag)
        return

    # Nowhere left to put it. The box keeps its color and the legend still
    # explains the color, which beats hiding a neighbour's tag under this one.


def _fill_tag(
    canvas: np.ndarray, tag: Rect, text: str, color: Color, scale: float, text_h: int
) -> None:
    left, top, right, bottom = tag
    cv2.rectangle(canvas, (left, top), (right, bottom), color, cv2.FILLED)
    cv2.putText(
        canvas,
        text,
        (left + _PAD, top + _PAD + text_h),
        _FONT,
        scale,
        (0, 0, 0),
        max(1, round(scale)),
        cv2.LINE_AA,
    )


def _draw_legend(
    canvas: np.ndarray,
    class_ids: Iterable[int],
    class_names: Sequence[str],
    palette: Sequence[Color],
    base_scale: float,
) -> Rect:
    """Draw a color key for the classes in this image; return the space it took.

    With crowded boxes some tags have nowhere to go, so the color has to carry
    the meaning on its own. The key is what makes that readable.
    """
    scale = base_scale * 0.8
    entries = [(cid, class_label(cid, class_names)) for cid in sorted(class_ids)]

    sizes = [cv2.getTextSize(name, _FONT, scale, 1)[0] for _, name in entries]
    text_h = max(size[1] for size in sizes)
    swatch = text_h
    row_h = text_h + 2 * _PAD
    width = swatch + 3 * _PAD + max(size[0] for size in sizes) + 2 * _PAD
    height = row_h * len(entries) + 2 * _PAD

    cv2.rectangle(canvas, (0, 0), (width, height), (0, 0, 0), cv2.FILLED)

    for row, (class_id, name) in enumerate(entries):
        top = _PAD + row * row_h
        color = palette[class_id % len(palette)] if palette else (0, 255, 0)
        cv2.rectangle(canvas, (_PAD, top), (_PAD + swatch, top + text_h), color, cv2.FILLED)
        cv2.putText(
            canvas,
            name,
            (swatch + 3 * _PAD, top + text_h),
            _FONT,
            scale,
            (255, 255, 255),
            max(1, round(scale)),
            cv2.LINE_AA,
        )

    return (0, 0, width, height)


def _overlaps(a: Rect, b: Rect) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
