"""Command line entry point for the converter."""

import argparse
import json
import sys
from pathlib import Path

import yaml
from PIL import Image

from .boxes import AnnotationError
from .cli import READERS, add_source_arguments, load_dataset
from .conversion import ImageEntry, from_coco, label_path_for, to_coco, to_yolo_lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epi-convert",
        description="Convert a detection dataset between YOLO and COCO.",
    )
    add_source_arguments(parser)

    parser.add_argument("--coco", type=Path, help="COCO json to read, for the other direction")
    parser.add_argument("--out", type=Path, required=True, help="file (to coco) or folder (to yolo)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.coco:
            return _coco_to_yolo(args)
        return _yolo_to_coco(args)
    except (AnnotationError, ValueError, FileNotFoundError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _yolo_to_coco(args: argparse.Namespace) -> int:
    dataset = load_dataset(args)
    split = dataset.split(args.split)
    reader = READERS[args.format]

    entries: list[ImageEntry] = []
    skipped = 0

    for image_path, label_path in split.pairs():
        if not label_path.exists():
            skipped += 1
            continue

        with Image.open(image_path) as image:
            width, height = image.size

        entries.append(
            ImageEntry(image_path.name, width, height, tuple(reader(label_path)))
        )

    document = to_coco(entries, dataset.class_names)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2, ensure_ascii=False))

    print(
        f"{len(entries)} imagens, {len(document['annotations'])} anotações"
        f" -> {args.out}"
    )
    if skipped:
        print(f"{skipped} imagens sem label ficaram de fora")
    return 0


def _coco_to_yolo(args: argparse.Namespace) -> int:
    document = json.loads(args.coco.read_text())
    entries, class_names = from_coco(document)

    labels_dir = args.out / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        # An image with no annotations gets an empty file, not no file: in YOLO
        # those mean different things, and the missing one means "not done yet".
        label_path_for(entry.file_name, labels_dir).write_text(to_yolo_lines(entry.boxes))

    (args.out / "data.yaml").write_text(
        yaml.safe_dump(
            {
                "train": "images",
                "nc": len(class_names),
                "names": list(class_names),
            },
            sort_keys=False,
            allow_unicode=True,
        )
    )

    total = sum(len(entry.boxes) for entry in entries)
    print(f"{len(entries)} labels, {total} anotações -> {labels_dir}")
    print(f"classes: {', '.join(class_names)}")
    print("as imagens não vêm no COCO; copie-as para <out>/images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
