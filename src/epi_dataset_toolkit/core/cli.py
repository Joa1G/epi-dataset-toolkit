"""Argument handling shared by every command in the toolkit.

The five tools all answer the same question first — which images, which
labels, which class names — so they ask it the same way, and a fix to the
resolution rules reaches all of them at once.
"""

import argparse
from pathlib import Path

from .datasets import Dataset, dataset_from_dirs, load_yolo_dataset
from .formats import AnnotationReader, read_yolo

READERS: dict[str, AnnotationReader] = {"yolo": read_yolo}


def add_source_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the flags that say where the dataset is."""
    source = parser.add_argument_group("dataset source")
    source.add_argument("--data", type=Path, help="path to data.yaml")
    source.add_argument("--images", type=Path, help="image folder, instead of --data")
    source.add_argument("--labels", type=Path, help="label folder (default: sibling 'labels')")
    source.add_argument("--names", help="comma-separated class names, required with --images")

    parser.add_argument("--split", default="train", help="split to use (default: train)")
    parser.add_argument("--format", choices=sorted(READERS), default="yolo")


def load_dataset(args: argparse.Namespace) -> Dataset:
    """Build the Dataset the flags describe, or explain what is missing."""
    if args.data:
        if args.names:
            raise ValueError("--names is only for --images; data.yaml owns the class names")
        return load_yolo_dataset(args.data)

    if not args.images:
        raise ValueError("pass either --data or --images")
    if not args.names:
        raise ValueError("--images also needs --names")

    names = [name.strip() for name in args.names.split(",") if name.strip()]
    return dataset_from_dirs(args.images, args.labels, names, split_name=args.split)
