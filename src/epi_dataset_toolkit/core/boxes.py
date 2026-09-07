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

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Normalized (left, top, right, bottom), the form overlap math needs."""
        return (
            self.x_center - self.width / 2,
            self.y_center - self.height / 2,
            self.x_center + self.width / 2,
            self.y_center + self.height / 2,
        )

    def intersection(self, other: "Box") -> float:
        """Normalized area shared with `other`; 0.0 when they do not touch."""
        left = max(self.bounds[0], other.bounds[0])
        top = max(self.bounds[1], other.bounds[1])
        right = min(self.bounds[2], other.bounds[2])
        bottom = min(self.bounds[3], other.bounds[3])
        return max(0.0, right - left) * max(0.0, bottom - top)

    def iou(self, other: "Box") -> float:
        """Intersection over union: 1.0 for identical boxes, 0.0 for disjoint."""
        overlap = self.intersection(other)
        union = self.area + other.area - overlap
        return overlap / union if union > 0 else 0.0
