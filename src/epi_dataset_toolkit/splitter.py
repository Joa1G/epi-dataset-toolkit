"""Command line entry point for the splitter."""

import argparse
import shutil
import sys
from pathlib import Path

import yaml

from .cli import add_source_arguments, load_dataset
from .duplicates import DEFAULT_DISTANCE, group_by_similarity, hash_images
from .splitting import assign_groups, parse_ratios


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epi-split",
        description="Split a dataset into train/valid/test without leaking duplicates.",
    )
    add_source_arguments(parser)

    parser.add_argument("--out", type=Path, required=True, help="folder to build the split in")
    parser.add_argument("--ratios", default="70/20/10", help="train/valid/test (default: 70/20/10)")
    parser.add_argument("--seed", type=int, default=0, help="same seed, same split (default: 0)")
    parser.add_argument(
        "--group-by",
        choices=("similarity", "none"),
        default="similarity",
        help="what must stay on one side of the split (default: similarity)",
    )
    parser.add_argument(
        "--distance",
        type=int,
        default=DEFAULT_DISTANCE,
        help=f"similarity threshold when grouping (default: {DEFAULT_DISTANCE})",
    )
    parser.add_argument("--symlink", action="store_true", help="link the files instead of copying")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        dataset = load_dataset(args)
        split = dataset.split(args.split)
        ratios = parse_ratios(args.ratios)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    labelled = [(image, label) for image, label in split.pairs() if label.exists()]
    skipped = sum(1 for _, label in split.pairs() if not label.exists())
    if not labelled:
        print("error: nenhuma imagem com label para dividir", file=sys.stderr)
        return 2

    images = [image for image, _ in labelled]
    if args.group_by == "similarity":
        groups = group_by_similarity(list(hash_images(images)), args.distance)
        grouped = sum(1 for group in groups if len(group) > 1)
        print(f"{len(images)} imagens em {len(groups)} grupos ({grouped} com duplicatas)")
    else:
        # Every image on its own: near-identical frames can land on both sides.
        groups = [[image] for image in images]
        print(f"{len(images)} imagens, sem agrupamento — duplicatas podem vazar")

    assignment = assign_groups(groups, ratios, seed=args.seed)
    labels = {image: label for image, label in labelled}

    for name, paths in assignment.items():
        images_dir = args.out / name / "images"
        labels_dir = args.out / name / "labels"
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)

        for image in paths:
            _place(image, images_dir / image.name, args.symlink)
            _place(labels[image], labels_dir / labels[image].name, args.symlink)

    _write_data_yaml(args.out, dataset.class_names, assignment)

    total = sum(len(paths) for paths in assignment.values())
    print()
    for name, paths in assignment.items():
        print(f"  {name:<6} {len(paths):>4}  {100 * len(paths) / total:5.1f}%")
    if skipped:
        print(f"\n{skipped} imagens sem label ficaram de fora")
    print(f"\nescrito em {args.out}, com data.yaml")
    return 0


def _place(source: Path, target: Path, symlink: bool) -> None:
    target.unlink(missing_ok=True)
    if symlink:
        target.symlink_to(source.resolve())
    else:
        shutil.copy2(source, target)


def _write_data_yaml(root: Path, class_names: tuple[str, ...], assignment: dict) -> None:
    """Write the data.yaml that makes the result loadable by --data."""
    config = {
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(class_names),
        "names": list(class_names),
    }
    (root / "data.yaml").write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))


if __name__ == "__main__":
    raise SystemExit(main())
