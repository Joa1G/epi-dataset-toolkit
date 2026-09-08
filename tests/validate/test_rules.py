"""Structural checks and declared relation rules."""

import pytest

from yolo_dataset_toolkit.core.boxes import AnnotationError, Box
from yolo_dataset_toolkit.validate.rules import RuleSet, check_image

NAMES = ["head", "helmet", "person", "reflective-vest"]

PERSON = Box(2, 0.5, 0.5, 0.1, 0.3)
HELMET_ON_PERSON = Box(1, 0.5, 0.38, 0.04, 0.05)

EPI_RULES = {
    "rules": [
        {"class": "person", "contains_any": ["head", "helmet"], "name": "person-sem-cabeca"},
        {"class": "head", "within_any": ["person"], "name": "head-sem-person"},
        {"class": "reflective-vest", "within_any": ["person"], "name": "colete-sem-person"},
        {"exclusive": ["head", "helmet"], "iou": 0.5, "name": "head-e-helmet-juntos"},
    ]
}


def rules_found(*boxes: Box, document=EPI_RULES, names=NAMES) -> set[str]:
    resolved = RuleSet.from_document(document).resolve(names)
    return {finding.rule for finding in check_image(boxes, names, resolved)}


# --- structure, which needs no rules at all -------------------------------


def test_structural_checks_run_without_any_rules():
    findings = check_image([Box(2, 0.98, 0.5, 0.2, 0.3)], NAMES)
    assert {finding.rule for finding in findings} == {"fora-da-imagem"}


def test_a_stray_click_is_degenerate():
    findings = check_image([Box(1, 0.5, 0.5, 0.0, 0.0)], NAMES)
    assert "caixa-degenerada" in {finding.rule for finding in findings}


def test_an_id_the_dataset_does_not_declare():
    findings = check_image([Box(9, 0.5, 0.5, 0.1, 0.1)], NAMES)
    assert "classe-desconhecida" in {finding.rule for finding in findings}


def test_the_same_box_annotated_twice():
    findings = check_image([PERSON, PERSON], NAMES)
    assert "caixa-duplicada" in {finding.rule for finding in findings}


def test_without_rules_no_relation_is_ever_reported():
    """A lone person is only a problem once someone declares it is."""
    assert check_image([PERSON], NAMES) == []


# --- relations ------------------------------------------------------------


def test_a_person_wearing_a_helmet_is_clean():
    assert rules_found(PERSON, HELMET_ON_PERSON) == set()


def test_contains_any_fires_when_nothing_is_inside():
    assert "person-sem-cabeca" in rules_found(PERSON)


def test_within_any_fires_when_there_is_no_container():
    loose_head = Box(0, 0.9, 0.9, 0.04, 0.04)
    assert "head-sem-person" in rules_found(PERSON, HELMET_ON_PERSON, loose_head)


def test_a_loose_helmet_is_allowed_because_no_rule_forbids_it():
    loose_helmet = Box(1, 0.9, 0.9, 0.04, 0.04)
    assert rules_found(PERSON, HELMET_ON_PERSON, loose_helmet) == set()


def test_exclusive_fires_when_two_classes_share_an_object():
    head = Box(0, 0.5, 0.38, 0.04, 0.05)
    assert "head-e-helmet-juntos" in rules_found(PERSON, HELMET_ON_PERSON, head)


def test_contains_and_within_are_not_the_same_direction():
    """Regression: the association test takes (part, whole) and is asymmetric.

    A head off to one side of a person sits inside the person's horizontal
    span, while the person's center falls outside the head's. Reading both
    rules in the same direction turns every such head into a false finding -
    which is exactly what happened, 1 real finding became 18.
    """
    names = ["head", "person"]
    person = Box(1, 0.5, 0.5, 0.2, 0.3)
    head = Box(0, 0.57, 0.42, 0.04, 0.05)
    contains = {"rules": [{"class": "person", "contains_any": ["head"]}]}
    within = {"rules": [{"class": "head", "within_any": ["person"]}]}

    assert rules_found(person, head, document=contains, names=names) == set()
    assert rules_found(person, head, document=within, names=names) == set()


# --- the association predicates -------------------------------------------


def test_aligned_accepts_a_helmet_poking_above_the_body():
    """Real annotation from the dataset: 48% of the helmet lies outside."""
    person = Box(1, 0.26, 0.4060215053763441, 0.05548387096774192, 0.11469534050179213)
    helmet = Box(0, 0.24100547667640618, 0.3505056156115611, 0.0229051345676655, 0.03863202183492312)

    names = ["helmet", "person"]
    document = {"rules": [{"class": "helmet", "within_any": ["person"]}]}
    assert rules_found(person, helmet, document=document, names=names) == set()


def test_inside_is_stricter_than_aligned():
    """Same boxes, stricter predicate, and now it is a finding."""
    person = Box(1, 0.5, 0.5, 0.2, 0.2)
    above = Box(0, 0.5, 0.38, 0.05, 0.06)  # touches the person, center above its top

    names = ["helmet", "person"]
    rule = {"class": "helmet", "within_any": ["person"], "name": "solto"}

    assert rules_found(person, above, document={"rules": [rule]}, names=names) == set()
    assert "solto" in rules_found(
        person, above, document={"association": "inside", "rules": [rule]}, names=names
    )


# --- the rules file itself ------------------------------------------------


def test_a_rule_naming_a_class_the_dataset_lacks_is_an_error():
    document = {"rules": [{"class": "unicorn", "within_any": ["person"]}]}
    with pytest.raises(AnnotationError, match="unicorn"):
        RuleSet.from_document(document).resolve(NAMES)


def test_an_unknown_association_is_rejected():
    with pytest.raises(AnnotationError, match="association"):
        RuleSet.from_document({"association": "telepathy", "rules": []})


def test_a_rule_without_a_direction_is_rejected():
    with pytest.raises(AnnotationError, match="contains_any"):
        RuleSet.from_document({"rules": [{"class": "person"}]})


def test_an_empty_rules_file_is_rejected():
    with pytest.raises(AnnotationError, match="nenhuma regra"):
        RuleSet.from_document({})


def test_exclusive_needs_two_classes():
    with pytest.raises(AnnotationError, match="duas classes"):
        RuleSet.from_document({"rules": [{"exclusive": ["head"]}]})


def test_rule_names_are_derived_when_not_given():
    ruleset = RuleSet.from_document({"rules": [{"class": "person", "contains_any": ["head"]}]})
    assert ruleset.relations[0].name == "person-sem-head"
