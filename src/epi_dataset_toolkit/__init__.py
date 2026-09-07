"""Tools for auditing and curating PPE object-detection datasets.

Layout: core/ holds what more than one tool needs, and each remaining folder
is one command. No tool folder imports another - anything two of them share
has moved into core/ by that fact alone.
"""

from .convert.coco import ImageEntry, from_coco, to_coco
from .core.boxes import AnnotationError, Box
from .core.datasets import Dataset, Split, dataset_from_dirs, load_yolo_dataset
from .core.formats import read_yolo
from .core.similarity import group_by_similarity, hash_images
from .split.assignment import assign_groups
from .validate.rules import Finding, Roles, check_image
from .visualize.palette import build_palette
from .visualize.rendering import draw_boxes

__all__ = [
    "AnnotationError",
    "Box",
    "Dataset",
    "Finding",
    "ImageEntry",
    "Roles",
    "Split",
    "assign_groups",
    "build_palette",
    "check_image",
    "dataset_from_dirs",
    "draw_boxes",
    "from_coco",
    "group_by_similarity",
    "hash_images",
    "load_yolo_dataset",
    "read_yolo",
    "to_coco",
]
