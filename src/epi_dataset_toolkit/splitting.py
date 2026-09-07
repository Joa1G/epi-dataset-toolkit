"""Assigning groups of images to train/valid/test.

Pure: takes groups and ratios, returns names. The point of taking *groups*
rather than images is that the group is what must not be broken apart - near
duplicate frames, or every frame from one video, depending on what the caller
decided is too similar to sit on both sides of the split.
"""

import random
from collections.abc import Sequence
from pathlib import Path

DEFAULT_RATIOS = {"train": 0.7, "valid": 0.2, "test": 0.1}


def assign_groups(
    groups: Sequence[Sequence[Path]],
    ratios: dict[str, float] = DEFAULT_RATIOS,
    seed: int = 0,
) -> dict[str, list[Path]]:
    """Spread `groups` over the splits, keeping each group whole.

    Groups differ in size, so handing out a fixed count of them would miss the
    target ratios. Each group instead goes to whichever split is furthest below
    its quota in images, which lands close to the ratios without ever splitting
    a group. The seed only decides the order groups are considered, so the same
    seed gives the same split.
    """
    if not ratios or any(share <= 0 for share in ratios.values()):
        raise ValueError("every ratio must be positive")

    total_images = sum(len(group) for group in groups)
    total_share = sum(ratios.values())
    quota = {name: total_images * share / total_share for name, share in ratios.items()}

    shuffled = list(groups)
    random.Random(seed).shuffle(shuffled)
    # Biggest first: a large group placed last would blow past whatever quota
    # is left, so it gets to pick while there is still room.
    shuffled.sort(key=len, reverse=True)

    result: dict[str, list[Path]] = {name: [] for name in ratios}
    for group in shuffled:
        target = max(result, key=lambda name: quota[name] - len(result[name]))
        result[target].extend(group)

    return {name: sorted(paths) for name, paths in result.items()}


def parse_ratios(text: str) -> dict[str, float]:
    """'70/20/10' -> {'train': 0.7, 'valid': 0.2, 'test': 0.1}."""
    parts = [part.strip() for part in text.split("/")]
    if len(parts) != 3:
        raise ValueError(f"expected three ratios like 70/20/10, got {text!r}")

    try:
        values = [float(part) for part in parts]
    except ValueError as exc:
        raise ValueError(f"invalid ratios {text!r}: {exc}") from exc

    if any(value <= 0 for value in values):
        raise ValueError(f"every ratio must be positive, got {text!r}")

    total = sum(values)
    return {name: value / total for name, value in zip(("train", "valid", "test"), values)}
