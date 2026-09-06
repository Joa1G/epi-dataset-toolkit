"""Core geometry type, shared by every tool in the toolkit."""

from dataclasses import dataclass


class AnnotationError(ValueError):
    """Raised when a label file exists but cannot be parsed."""


@dataclass(frozen=True, slots=True)
class Box:
    """A single annotated object, in YOLO normalized coordinates.

    The four coordinates are fractions of the image size (0.0 to 1.0), so a Box
    stays valid if the image is resized. On purpose, nothing here knows about
    files, OpenCV or the YOLO text format: this is the vocabulary every other
    module speaks, which is what lets them be swapped independently.
    """

    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float

    def to_corners(self, img_width: int, img_height: int) -> tuple[int, int, int, int]:
        """Convert to pixel corners (x1, y1, x2, y2), the form drawing needs."""
        half_w = self.width / 2
        half_h = self.height / 2
        return (
            round((self.x_center - half_w) * img_width),
            round((self.y_center - half_h) * img_height),
            round((self.x_center + half_w) * img_width),
            round((self.y_center + half_h) * img_height),
        )

    @property
    def area(self) -> float:
        """Normalized area. Near-zero means a degenerate box (Step 3 checks this)."""
        return self.width * self.height
