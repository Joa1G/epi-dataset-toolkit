"""Annotation readers: one function per on-disk format."""

from pathlib import Path
from typing import Protocol

from .boxes import AnnotationError, Box


class AnnotationReader(Protocol):
    """Everything the rest of the toolkit needs from an annotation format.

    Any callable with this shape can be dropped in, so adding COCO support in
    Step 5 means writing read_coco() and changing nothing else.
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
