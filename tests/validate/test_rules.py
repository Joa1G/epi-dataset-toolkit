"""The rules from ANNOTATION_GUIDE.md, as executable checks."""

from epi_dataset_toolkit.core.boxes import Box
from epi_dataset_toolkit.validate.rules import Roles, check_image

NAMES = ["head", "helmet", "person", "reflective-vest"]
ROLES = Roles.from_names(NAMES)

PERSON = Box(2, 0.5, 0.5, 0.1, 0.3)
HELMET_ON_PERSON = Box(1, 0.5, 0.38, 0.04, 0.05)


def rules_found(*boxes: Box) -> set[str]:
    return {finding.rule for finding in check_image(boxes, NAMES, ROLES)}


def test_a_person_wearing_a_helmet_is_clean():
    assert rules_found(PERSON, HELMET_ON_PERSON) == set()


def test_person_without_head_or_helmet_breaks_rule_three():
    assert "person-sem-cabeca" in rules_found(PERSON)


def test_a_loose_helmet_is_allowed_but_a_loose_head_is_not():
    """Rule 5 exempts the helmet; a bare head implies a person by rules 1 and 3."""
    loose_helmet = Box(1, 0.9, 0.9, 0.04, 0.04)
    loose_head = Box(0, 0.9, 0.9, 0.04, 0.04)

    assert "head-sem-person" not in rules_found(PERSON, HELMET_ON_PERSON, loose_helmet)
    assert "head-sem-person" in rules_found(PERSON, HELMET_ON_PERSON, loose_head)


def test_a_vest_on_the_ground_breaks_rule_five():
    on_the_ground = Box(3, 0.9, 0.9, 0.05, 0.03)
    assert "colete-sem-person" in rules_found(PERSON, HELMET_ON_PERSON, on_the_ground)


def test_head_and_helmet_on_the_same_head_contradict():
    head = Box(0, 0.5, 0.38, 0.04, 0.05)
    assert "head-e-helmet-juntos" in rules_found(PERSON, HELMET_ON_PERSON, head)


def test_the_same_box_annotated_twice_is_reported():
    assert "caixa-duplicada" in rules_found(PERSON, PERSON, HELMET_ON_PERSON)


def test_a_stray_click_is_degenerate():
    assert "caixa-degenerada" in rules_found(PERSON, HELMET_ON_PERSON, Box(1, 0.5, 0.5, 0.0, 0.0))


def test_a_box_running_off_the_image_is_reported():
    assert "fora-da-imagem" in rules_found(Box(2, 0.98, 0.5, 0.2, 0.3))


def test_a_dataset_without_these_classes_skips_the_rule_checks():
    """The structural checks are universal; the guide's rules are not."""
    other = ["car", "truck"]
    findings = check_image([Box(0, 0.5, 0.5, 0.2, 0.2)], other, Roles.from_names(other))
    assert findings == []
