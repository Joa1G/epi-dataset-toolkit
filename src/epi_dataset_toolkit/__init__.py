"""Tools for auditing and curating PPE object-detection datasets."""

from .boxes import AnnotationError, Box
from .conversion import ImageEntry, from_coco, to_coco
from .datasets import Dataset, Split, dataset_from_dirs, load_yolo_dataset
from .duplicates import group_by_similarity, hash_images
from .formats import read_yolo
from .palette import build_palette
from .rendering import draw_boxes
from .splitting import assign_groups
from .validation import Finding, Roles, check_image

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
    "from_coco",
    "group_by_similarity",
    "draw_boxes",
    "hash_images",
    "load_yolo_dataset",
    "read_yolo",
    "to_coco",
]
