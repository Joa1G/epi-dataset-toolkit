"""Finding near-identical images.

Frames pulled from video are the reason this exists: two frames a second
apart are different files with almost the same pixels. Split them at random
and the model meets the test set during training, which shows up as a score
that does not survive contact with new footage.
"""

from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

import imagehash
from PIL import Image

# Hamming distance between two perceptual hashes. 0 is pixel-identical after
# downscaling; the useful band for consecutive video frames sits just above it.
DEFAULT_DISTANCE = 4

Signature = tuple[Path, imagehash.ImageHash]


def hash_images(paths: Iterable[Path]) -> Iterator[Signature]:
    """Perceptual hash per image, skipping the ones that will not open."""
    for path in paths:
        try:
            with Image.open(path) as image:
                yield path, imagehash.phash(image)
        except OSError:
            continue


def group_by_similarity(
    signatures: Sequence[Signature], distance: int = DEFAULT_DISTANCE
) -> list[list[Path]]:
    """Cluster images whose hashes are within `distance` of each other.

    Similarity is not transitive - A can resemble B and B resemble C while A
    and C look nothing alike - but for splitting that does not matter: what
    must not happen is any pair straddling two splits, so the transitive
    closure is exactly the right unit. Union-find gives it directly.
    """
    parent = list(range(len(signatures)))

    def root(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for first in range(len(signatures)):
        for second in range(first + 1, len(signatures)):
            if signatures[first][1] - signatures[second][1] <= distance:
                parent[root(first)] = root(second)

    clusters: dict[int, list[Path]] = {}
    for position, (path, _) in enumerate(signatures):
        clusters.setdefault(root(position), []).append(path)

    return [sorted(group) for group in clusters.values()]
