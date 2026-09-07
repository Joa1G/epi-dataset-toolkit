"""Annotation readers: one function per on-disk format."""

from pathlib import Path
from typing import Protocol

from .boxes import AnnotationError, Box


class AnnotationReader(Protocol):
    """Everything the rest of the toolkit needs from an annotation format.

    One file per image is the assumption baked into this shape, and it holds
    for YOLO and for the per-image XML formats. It does not hold for COCO,
    whose single document describes the whole dataset and carries the image
    dimensions the boxes are measured against - so COCO is not a reader here
    but a conversion, in conversion.py. Writing the converter is what showed
    this Protocol has a boundary; it is drawn here on purpose rather than
    stretched to hide it.
    """

    def __call__(self, path: Path) -> list[Box]: ...


def read_yolo(path: Path) -> list[Box]:
    """Parse one YOLO .txt file: one object per line, 'class xc yc w h'.

    Malformed lines raise instead of being silently dropped. Deciding what to
    do about them is the caller's job, and auditing them is Step 3's job.
    """
    boxes: list[Box] = []

    for number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        fields = line.split()
        if len(fields) != 5:
            raise AnnotationError(
                f"{path.name}:{number}: expected 5 fields, got {len(fields)}"
            )

        try:
            class_id = int(fields[0])
            x_center, y_center, width, height = (float(field) for field in fields[1:])
        except ValueError as exc:
            raise AnnotationError(f"{path.name}:{number}: {exc}") from exc

        boxes.append(Box(class_id, x_center, y_center, width, height))

    return boxes
