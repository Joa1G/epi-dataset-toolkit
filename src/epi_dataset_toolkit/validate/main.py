"""Command line entry point for the validator."""

import argparse
import sys
from collections import Counter
from pathlib import Path

from ..core.boxes import AnnotationError, Box
from ..core.cli import READERS, add_source_arguments, load_dataset
from ..core.datasets import IMAGE_SUFFIXES
from .rules import Finding, Roles, check_image

# Enough lines to see the shape of a problem without burying the summary.
_EXAMPLES_PER_RULE = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epi-validate",
        description="Audit a detection dataset for broken labels and rule violations.",
    )
    add_source_arguments(parser)

    parser.add_argument("--limit", type=int, default=0, help="how many images (0 = all)")
    parser.add_argument(
        "--examples",
        type=int,
        default=_EXAMPLES_PER_RULE,
        help=f"lines shown per problem (default: {_EXAMPLES_PER_RULE}, 0 = all)",
    )
    parser.add_argument(
        "--no-rules",
        dest="rules",
        action="store_false",
        help="check only structure, skipping the ANNOTATION_GUIDE.md rules",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when anything at all is found, warnings included",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        dataset = load_dataset(args)
        split = dataset.split(args.split)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    reader = READERS[args.format]
    # The guide's rules describe this dataset's conventions. Another dataset
    # may annotate the same classes by different ones, and reporting that as
    # hundreds of errors would say more about us than about it.
    roles = Roles.from_names(dataset.class_names) if args.rules else Roles()

    found: dict[str, list[str]] = {}
    counts: Counter[int] = Counter()
    images = empty = unlabeled = broken = 0

    for image_path, label_path in split.pairs(limit=args.limit or None):
        images += 1

        if not label_path.exists():
            unlabeled += 1
            _record(found, "sem-label", f"{image_path.name}: nenhum .txt correspondente")
            continue

        try:
            boxes = reader(label_path)
        except AnnotationError as exc:
            broken += 1
            _record(found, "label-ilegivel", str(exc))
            continue

        if not boxes:
            empty += 1
        counts.update(box.class_id for box in boxes)

        for finding in check_image(boxes, dataset.class_names, roles):
            _record(found, finding.rule, f"{image_path.name}: {finding.detail}")

    for orphan in _orphan_labels(split):
        _record(found, "label-orfa", f"{orphan}: .txt sem imagem correspondente")

    _report(dataset.class_names, counts, images, empty, unlabeled, broken, found, args.examples)

    if args.strict:
        return 1 if found else 0
    # Only a label we could not read or match is a hard failure; a rule
    # violation is a judgement call for a human, not grounds for a red build.
    return 1 if {"sem-label", "label-ilegivel", "label-orfa"} & found.keys() else 0


def _record(found: dict[str, list[str]], rule: str, line: str) -> None:
    found.setdefault(rule, []).append(line)


def _orphan_labels(split) -> list[str]:
    """Label files with no image beside them - usually a rename gone wrong."""
    if not split.labels_dir.is_dir():
        return []

    stems = {
        path.stem
        for path in split.images_dir.iterdir()
        if path.suffix.lower() in IMAGE_SUFFIXES
    }
    return sorted(
        path.name for path in split.labels_dir.glob("*.txt") if path.stem not in stems
    )


def _report(
    class_names: tuple[str, ...],
    counts: Counter,
    images: int,
    empty: int,
    unlabeled: int,
    broken: int,
    found: dict[str, list[str]],
    examples: int,
) -> None:
    print(f"\n{images} imagens | {empty} sem objeto | {unlabeled} sem label | {broken} ilegíveis")

    total = sum(counts.values())
    if total:
        print(f"\n{total} caixas:")
        width = max(len(name) for name in class_names) if class_names else 0
        for class_id, count in counts.most_common():
            name = class_names[class_id] if 0 <= class_id < len(class_names) else f"class_{class_id}"
            share = 100 * count / total
            print(f"  {name:<{width}}  {count:>6}  {share:5.1f}%")

    if not found:
        print("\nnenhum problema encontrado")
        return

    print(f"\n{sum(len(lines) for lines in found.values())} problemas:")
    for rule, lines in sorted(found.items(), key=lambda item: -len(item[1])):
        print(f"\n  {rule} ({len(lines)})")
        shown = lines if examples == 0 else lines[:examples]
        for line in shown:
            print(f"    {line}")
        if len(lines) > len(shown):
            print(f"    ... e mais {len(lines) - len(shown)}")


if __name__ == "__main__":
    raise SystemExit(main())
