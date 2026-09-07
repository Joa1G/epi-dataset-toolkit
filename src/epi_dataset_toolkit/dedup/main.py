"""Command line entry point for the deduplicator."""

import argparse
import sys

from ..core.cli import add_source_arguments, load_dataset
from ..core.similarity import DEFAULT_DISTANCE, group_by_similarity, hash_images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epi-dedup",
        description="Find near-identical images, the ones that leak across a split.",
    )
    add_source_arguments(parser)

    parser.add_argument(
        "--distance",
        type=int,
        default=DEFAULT_DISTANCE,
        help=f"how alike counts as duplicate, 0 = identical (default: {DEFAULT_DISTANCE})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually delete the extras, keeping the first of each group",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        split = load_dataset(args).split(args.split)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    images = [image for image, _ in split.pairs()]
    signatures = list(hash_images(images))
    groups = [group for group in group_by_similarity(signatures, args.distance) if len(group) > 1]

    duplicates = sum(len(group) - 1 for group in groups)
    print(f"{len(signatures)} imagens | {len(groups)} grupos duplicados | {duplicates} a descartar")

    for group in sorted(groups, key=len, reverse=True):
        keep, *extras = group
        print(f"\n  manter  {keep.name}")
        for extra in extras:
            print(f"  {'apagar' if args.apply else 'sobra '}  {extra.name}")

    if not args.apply:
        if duplicates:
            print(f"\nnada foi apagado; --apply remove as {duplicates} sobras e seus labels")
        return 0

    removed = 0
    for group in groups:
        for extra in group[1:]:
            extra.unlink()
            label = split.labels_dir / f"{extra.stem}.txt"
            label.unlink(missing_ok=True)
            removed += 1

    print(f"\n{removed} imagens removidas, com os labels correspondentes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
