"""Finding images and their labels on disk, whatever the folder layout is."""

import os
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

# Exports disagree on this one: Roboflow writes "val", plenty of others "valid".
_SPLIT_KEYS = {
    "train": ("train",),
    "valid": ("val", "valid"),
    "test": ("test",),
}


@dataclass(frozen=True, slots=True)
class Split:
    """One partition of a dataset: a folder of images and its sibling labels."""

    name: str
    images_dir: Path
    labels_dir: Path

    def pairs(
        self,
        suffixes: Sequence[str] = IMAGE_SUFFIXES,
        limit: int | None = None,
    ) -> Iterator[tuple[Path, Path]]:
        """Yield (image, expected label) pairs. The label may not exist yet."""
        images = sorted(
            path
            for path in self.images_dir.iterdir()
            if path.suffix.lower() in suffixes
        )
        if limit is not None:
            images = images[:limit]

        for image_path in images:
            yield image_path, self.labels_dir / f"{image_path.stem}.txt"


@dataclass(frozen=True, slots=True)
class Dataset:
    """Class names plus whichever splits actually exist on disk."""

    class_names: tuple[str, ...]
    splits: dict[str, Split]

    def split(self, name: str) -> Split:
        if name not in self.splits:
            available = ", ".join(sorted(self.splits)) or "none"
            raise ValueError(f"split {name!r} not found (available: {available})")
        return self.splits[name]


def load_yolo_dataset(data_yaml: Path) -> Dataset:
    """Read a data.yaml and locate the split folders it points at.

    The class names come from the file and only from the file: it is the one
    place that maps a class id to a meaning, and a copy that can drift is worse
    than no copy at all.
    """
    config = yaml.safe_load(data_yaml.read_text()) or {}

    names = config.get("names")
    if isinstance(names, dict):
        # Some exports index names by id: {0: 'head', 1: 'helmet'}.
        names = [names[key] for key in sorted(names)]
    if not names:
        raise ValueError(f"{data_yaml} has no 'names' entry")

    root = data_yaml.parent
    splits: dict[str, Split] = {}

    for split_name, keys in _SPLIT_KEYS.items():
        images_dir = _resolve_images_dir(root, config, keys, split_name)
        if images_dir is not None:
            splits[split_name] = Split(split_name, images_dir, images_dir.parent / "labels")

    return Dataset(tuple(names), splits)


def dataset_from_dirs(
    images_dir: Path,
    labels_dir: Path | None,
    class_names: Sequence[str],
    split_name: str = "custom",
) -> Dataset:
    """Build a Dataset from explicit folders, for data that has no data.yaml."""
    labels_dir = labels_dir or images_dir.parent / "labels"
    split = Split(split_name, images_dir, labels_dir)
    return Dataset(tuple(class_names), {split_name: split})


def _resolve_images_dir(
    root: Path, config: dict, keys: Sequence[str], split_name: str
) -> Path | None:
    """Find a split's image folder, tolerating the paths data.yaml usually has.

    Roboflow writes "../train/images", which assumes data.yaml was copied one
    level deeper than where it ships. So each candidate is tried in turn and
    the first one that exists wins.
    """
    candidates: list[Path] = []

    for key in keys:
        raw = config.get(key)
        if not isinstance(raw, str):
            continue
        raw_path = Path(raw)
        candidates.append(root / raw_path)
        stripped = [part for part in raw_path.parts if part not in ("..", ".")]
        if stripped:
            candidates.append(root.joinpath(*stripped))

    candidates.append(root / split_name / "images")

    for candidate in candidates:
        normalized = Path(os.path.normpath(candidate))
        if normalized.is_dir():
            return normalized

    return None
