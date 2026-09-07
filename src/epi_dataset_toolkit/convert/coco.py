"""Converting between YOLO and COCO.

COCO differs from YOLO in two ways at the same time, which is why converters
written from memory are subtly wrong and the error is invisible until someone
draws the boxes:

    YOLO   class_id  x_center y_center w h   fractions of the image
    COCO   bbox      x_min    y_min    w h   pixels

The anchor moves from the center to the top-left corner *and* the numbers stop
being normalized. Get one right and forget the other and every box lands
plausibly near where it belongs, just wrong.

The third trap has no arithmetic in it: YOLO class ids start at 0, COCO
category ids conventionally start at 1. Nothing here assumes that on the way
in - the categories are read in id order and their position is the YOLO index,
so a file numbered any other way still converts correctly.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.boxes import AnnotationError, Box


@dataclass(frozen=True, slots=True)
class ImageEntry:
    """One image and its boxes, with the size the pixel math needs."""

    file_name: str
    width: int
    height: int
    boxes: tuple[Box, ...]


def to_coco(entries: Iterable[ImageEntry], class_names: Sequence[str]) -> dict[str, Any]:
    """Build a COCO document from images already read as Boxes."""
    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []

    for image_id, entry in enumerate(entries, start=1):
        images.append(
            {
                "id": image_id,
                "file_name": entry.file_name,
                "width": entry.width,
                "height": entry.height,
            }
        )

        for box in entry.boxes:
            left, top, _, _ = box.bounds
            pixel_width = box.width * entry.width
            pixel_height = box.height * entry.height
            annotations.append(
                {
                    "id": len(annotations) + 1,
                    "image_id": image_id,
                    "category_id": box.class_id + 1,
                    "bbox": [
                        left * entry.width,
                        top * entry.height,
                        pixel_width,
                        pixel_height,
                    ],
                    "area": pixel_width * pixel_height,
                    "iscrowd": 0,
                }
            )

    return {
        "images": images,
        "annotations": annotations,
        "categories": [
            {"id": position + 1, "name": name, "supercategory": "none"}
            for position, name in enumerate(class_names)
        ],
    }


def from_coco(document: dict[str, Any]) -> tuple[list[ImageEntry], list[str]]:
    """Read a COCO document into entries plus the class names, in YOLO order."""
    categories = document.get("categories")
    if not categories:
        raise AnnotationError("COCO sem 'categories'")

    ordered = sorted(categories, key=lambda category: category["id"])
    class_names = [category["name"] for category in ordered]
    # Position in the sorted list, not the id itself: this is what makes a
    # 0-based or 1-based or gappy file all come out the same.
    class_of = {category["id"]: position for position, category in enumerate(ordered)}

    images = {image["id"]: image for image in document.get("images", [])}
    boxes: dict[int, list[Box]] = {image_id: [] for image_id in images}

    for annotation in document.get("annotations", []):
        image = images.get(annotation["image_id"])
        if image is None:
            raise AnnotationError(f"anotação {annotation.get('id')} aponta para imagem inexistente")

        width, height = image["width"], image["height"]
        if not width or not height:
            raise AnnotationError(f"imagem {image['file_name']} sem dimensões")

        left, top, box_width, box_height = annotation["bbox"]
        boxes[image["id"]].append(
            Box(
                class_of[annotation["category_id"]],
                (left + box_width / 2) / width,
                (top + box_height / 2) / height,
                box_width / width,
                box_height / height,
            )
        )

    entries = [
        ImageEntry(image["file_name"], image["width"], image["height"], tuple(boxes[image_id]))
        for image_id, image in images.items()
    ]
    return entries, class_names


def to_yolo_lines(boxes: Iterable[Box], digits: int = 6) -> str:
    """Render boxes back as the body of a YOLO .txt file."""
    return "".join(
        f"{box.class_id} {box.x_center:.{digits}f} {box.y_center:.{digits}f}"
        f" {box.width:.{digits}f} {box.height:.{digits}f}\n"
        for box in boxes
    )


def label_path_for(image_name: str, labels_dir: Path) -> Path:
    """Where the YOLO label for an image goes."""
    return labels_dir / f"{Path(image_name).stem}.txt"
