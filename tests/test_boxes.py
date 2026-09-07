"""Geometry, which every other check is built on."""

import pytest

from epi_dataset_toolkit.boxes import Box


def test_to_corners_anchors_on_the_center():
    box = Box(0, 0.5, 0.5, 0.2, 0.4)
    assert box.to_corners(100, 100) == (40, 30, 60, 70)


def test_disjoint_boxes_do_not_intersect():
    left = Box(0, 0.1, 0.1, 0.1, 0.1)
    right = Box(0, 0.9, 0.9, 0.1, 0.1)
    assert left.intersection(right) == 0.0
    assert left.iou(right) == 0.0


def test_identical_boxes_have_iou_of_one():
    box = Box(0, 0.5, 0.5, 0.3, 0.3)
    assert box.iou(Box(0, 0.5, 0.5, 0.3, 0.3)) == pytest.approx(1.0)


def test_a_helmet_can_belong_to_someone_while_half_outside_them():
    """Real annotation from the dataset, video_obra_1_00097."""
    person = Box(2, 0.26, 0.4060215053763441, 0.05548387096774192, 0.11469534050179213)
    helmet = Box(1, 0.24100547667640618, 0.3505056156115611, 0.0229051345676655, 0.03863202183492312)

    inside = helmet.intersection(person) / helmet.area
    assert inside == pytest.approx(0.483, abs=0.001)  # half of it hangs out
    assert helmet.intersection(person) > 0  # and yet it touches them
