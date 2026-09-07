"""Grouping near-identical images."""

from pathlib import Path

import imagehash

from epi_dataset_toolkit.duplicates import group_by_similarity


def signature(name: str, hex_hash: str):
    return Path(name), imagehash.hex_to_hash(hex_hash)


IDENTICAL = "f" * 16
ONE_BIT_OFF = "e" + "f" * 15
FAR_AWAY = "0" * 16


def test_identical_images_group_together():
    signatures = [signature("a.jpg", IDENTICAL), signature("b.jpg", IDENTICAL)]
    assert group_by_similarity(signatures, distance=0) == [[Path("a.jpg"), Path("b.jpg")]]


def test_different_images_stay_apart():
    signatures = [signature("a.jpg", IDENTICAL), signature("b.jpg", FAR_AWAY)]
    assert len(group_by_similarity(signatures, distance=4)) == 2


def test_similarity_is_closed_transitively():
    """A resembles B, B resembles C: all three must share a split.

    Chains like this are exactly what consecutive video frames produce, and
    leaving C out would put it on the far side of the split from A.
    """
    signatures = [
        signature("a.jpg", "ffffffffffffffff"),
        signature("b.jpg", "fffffffffffffffe"),
        signature("c.jpg", "fffffffffffffffc"),
    ]
    groups = group_by_similarity(signatures, distance=1)
    assert groups == [[Path("a.jpg"), Path("b.jpg"), Path("c.jpg")]]


def test_a_lone_image_is_its_own_group():
    assert group_by_similarity([signature("a.jpg", IDENTICAL)]) == [[Path("a.jpg")]]


def test_no_images_no_groups():
    assert group_by_similarity([]) == []
