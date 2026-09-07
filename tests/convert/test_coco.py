"""YOLO <-> COCO.

A round trip alone does not prove a converter correct: if both directions
share the same wrong convention, the error cancels itself and the test passes
happily. So the anchor and the scale are pinned down separately, against
numbers worked out by hand.
"""

import pytest

from epi_dataset_toolkit.core.boxes import AnnotationError, Box
from epi_dataset_toolkit.convert.coco import ImageEntry, from_coco, to_coco, to_yolo_lines

NAMES = ["head", "helmet", "person"]


def test_the_anchor_moves_from_the_center_to_the_corner():
    """A box centered at (0.5, 0.5) on a 200x100 image spans 50..150, 25..75."""
    box = Box(0, 0.5, 0.5, 0.5, 0.5)
    document = to_coco([ImageEntry("a.jpg", 200, 100, (box,))], NAMES)

    assert document["annotations"][0]["bbox"] == [50.0, 25.0, 100.0, 50.0]


def test_a_box_in_the_corner_stays_in_the_corner():
    """The test that fails loudly when only one of the two changes was made."""
    box = Box(0, 0.1, 0.1, 0.2, 0.2)
    document = to_coco([ImageEntry("a.jpg", 100, 100, (box,))], NAMES)

    assert document["annotations"][0]["bbox"] == [0.0, 0.0, 20.0, 20.0]


def test_area_is_in_pixels_not_fractions():
    box = Box(0, 0.5, 0.5, 0.5, 0.5)
    document = to_coco([ImageEntry("a.jpg", 200, 100, (box,))], NAMES)

    assert document["annotations"][0]["area"] == 100.0 * 50.0


def test_category_ids_are_one_based_on_the_way_out():
    """COCO numbers categories from 1; YOLO numbers classes from 0."""
    document = to_coco([ImageEntry("a.jpg", 10, 10, (Box(0, 0.5, 0.5, 0.1, 0.1),))], NAMES)

    assert [category["id"] for category in document["categories"]] == [1, 2, 3]
    assert document["annotations"][0]["category_id"] == 1


def test_reading_does_not_assume_how_the_categories_are_numbered():
    """Position in id order is the class id, whatever the file's own ids are."""
    document = {
        "images": [{"id": 1, "file_name": "a.jpg", "width": 100, "height": 100}],
        "annotations": [{"id": 1, "image_id": 1, "category_id": 40, "bbox": [0, 0, 10, 10]}],
        "categories": [
            {"id": 7, "name": "head"},
            {"id": 40, "name": "helmet"},
        ],
    }
    entries, names = from_coco(document)

    assert names == ["head", "helmet"]
    assert entries[0].boxes[0].class_id == 1  # helmet, the second category


def test_a_full_round_trip_returns_the_same_boxes():
    boxes = (
        Box(0, 0.5, 0.5, 0.2, 0.3),
        Box(2, 0.125, 0.875, 0.25, 0.25),
        Box(1, 0.9, 0.1, 0.05, 0.05),
    )
    entry = ImageEntry("a.jpg", 640, 480, boxes)

    back, names = from_coco(to_coco([entry], NAMES))

    assert names == NAMES
    for before, after in zip(boxes, back[0].boxes):
        assert after.class_id == before.class_id
        assert after.x_center == pytest.approx(before.x_center)
        assert after.y_center == pytest.approx(before.y_center)
        assert after.width == pytest.approx(before.width)
        assert after.height == pytest.approx(before.height)


def test_a_non_square_image_round_trips():
    """Where a converter that divides by the wrong side gives itself away."""
    box = Box(0, 0.25, 0.75, 0.5, 0.125)
    back, _ = from_coco(to_coco([ImageEntry("a.jpg", 1920, 1080, (box,))], NAMES))

    assert back[0].boxes[0].x_center == pytest.approx(0.25)
    assert back[0].boxes[0].height == pytest.approx(0.125)


def test_an_image_with_no_objects_survives_as_an_empty_file():
    entry = ImageEntry("empty.jpg", 100, 100, ())
    back, _ = from_coco(to_coco([entry], NAMES))

    assert back[0].boxes == ()
    assert to_yolo_lines(back[0].boxes) == ""


def test_yolo_lines_are_written_back_in_the_original_shape():
    line = to_yolo_lines([Box(2, 0.5, 0.25, 0.1, 0.2)])
    assert line == "2 0.500000 0.250000 0.100000 0.200000\n"


def test_a_coco_without_categories_is_rejected():
    with pytest.raises(AnnotationError):
        from_coco({"images": [], "annotations": []})


def test_an_annotation_pointing_nowhere_is_rejected():
    document = {
        "images": [{"id": 1, "file_name": "a.jpg", "width": 10, "height": 10}],
        "annotations": [{"id": 1, "image_id": 99, "category_id": 1, "bbox": [0, 0, 1, 1]}],
        "categories": [{"id": 1, "name": "head"}],
    }
    with pytest.raises(AnnotationError):
        from_coco(document)
