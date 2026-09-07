"""Command line entry point for the visualizer."""

import argparse
import sys
from pathlib import Path

import cv2

from .boxes import AnnotationError
from .cli import READERS, add_source_arguments, load_dataset
from .palette import Color, build_palette, parse_hex_color
from .rendering import draw_boxes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epi-visualize",
        description="Draw a detection dataset's bounding boxes onto its images.",
    )

    add_source_arguments(parser)

    parser.add_argument("--limit", type=int, default=30, help="how many images (0 = all)")
    parser.add_argument("--out", type=Path, default=Path("visualized"), help="output folder")
    parser.add_argument("--thickness", type=int, default=2, help="box line width in pixels")
    parser.add_argument(
        "--no-legend",
        dest="legend",
        action="store_false",
        help="drop the color key drawn in the corner",
    )
    parser.add_argument(
        "--color",
        action="append",
        default=[],
        metavar="NAME=#RRGGBB",
        help="override one class color, repeatable",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        dataset = load_dataset(args)
        split = dataset.split(args.split)
        palette = _build_palette(dataset.class_names, args.color)
    except (KeyError, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    reader = READERS[args.format]
    args.out.mkdir(parents=True, exist_ok=True)
    limit = args.limit or None

    written = missing = unreadable = broken = 0

    for image_path, label_path in split.pairs(limit=limit):
        if not label_path.exists():
            print(f"no label for {image_path.name}, skipping")
            missing += 1
            continue

        image = cv2.imread(str(image_path))
        if image is None:
            # imread returns None instead of raising on a corrupt or unsupported file.
            print(f"cannot read {image_path.name}, skipping")
            unreadable += 1
            continue

        try:
            boxes = reader(label_path)
        except AnnotationError as exc:
            print(f"bad label: {exc}")
            broken += 1
            continue

        canvas = draw_boxes(
            image,
            boxes,
            dataset.class_names,
            palette,
            thickness=args.thickness,
            legend=args.legend,
        )
        cv2.imwrite(str(args.out / image_path.name), canvas)
        written += 1

    print(
        f"\n{written} written to {args.out}"
        f" | {missing} without label | {unreadable} unreadable | {broken} malformed"
    )
    return 0


def _build_palette(class_names: tuple[str, ...], overrides: list[str]) -> list[Color]:
    palette = build_palette(len(class_names))

    for override in overrides:
        name, _, hex_color = override.partition("=")
        if name not in class_names:
            raise ValueError(f"unknown class {name!r} in --color")
        palette[class_names.index(name)] = parse_hex_color(hex_color)

    return palette


if __name__ == "__main__":
    raise SystemExit(main())
