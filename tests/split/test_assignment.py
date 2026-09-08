"""Splitting, where a mistake is invisible until the metrics lie."""

from pathlib import Path

import pytest

from yolo_dataset_toolkit.split.assignment import assign_groups, parse_ratios


def groups_of(*sizes: int) -> list[list[Path]]:
    return [
        [Path(f"g{index}_{member}.jpg") for member in range(size)]
        for index, size in enumerate(sizes)
    ]


def test_no_group_is_ever_split():
    groups = groups_of(7, 5, 3, 2, 2, 1, 1, 1, 1, 1)
    assignment = assign_groups(groups)

    for group in groups:
        homes = {name for name, paths in assignment.items() if set(group) & set(paths)}
        assert len(homes) == 1, f"{group} ficou em {homes}"


def test_every_image_lands_somewhere_exactly_once():
    groups = groups_of(4, 3, 2, 1, 1, 1)
    assignment = assign_groups(groups)

    placed = [path for paths in assignment.values() for path in paths]
    assert sorted(placed) == sorted(path for group in groups for path in group)


def test_ratios_are_approximately_honoured():
    groups = groups_of(*([1] * 100))
    assignment = assign_groups(groups, {"train": 0.7, "valid": 0.2, "test": 0.1})

    assert len(assignment["train"]) == pytest.approx(70, abs=2)
    assert len(assignment["valid"]) == pytest.approx(20, abs=2)
    assert len(assignment["test"]) == pytest.approx(10, abs=2)


def test_the_same_seed_gives_the_same_split():
    groups = groups_of(3, 2, 2, 1, 1, 1, 1)
    assert assign_groups(groups, seed=7) == assign_groups(groups, seed=7)


def test_a_group_bigger_than_a_quota_still_fits_somewhere():
    """One group holding most of the dataset must not crash the assignment."""
    assignment = assign_groups(groups_of(9, 1))
    assert sum(len(paths) for paths in assignment.values()) == 10


def test_ratios_must_be_positive():
    with pytest.raises(ValueError):
        assign_groups(groups_of(1), {"train": 1.0, "valid": 0.0, "test": 0.0})


def test_parse_ratios_normalises():
    assert parse_ratios("70/20/10") == {"train": 0.7, "valid": 0.2, "test": 0.1}
    assert parse_ratios("8/1/1") == {"train": 0.8, "valid": 0.1, "test": 0.1}


@pytest.mark.parametrize("text", ["70/30", "70/20/10/5", "a/b/c", "70/-20/10"])
def test_bad_ratios_are_rejected(text: str):
    with pytest.raises(ValueError):
        parse_ratios(text)
