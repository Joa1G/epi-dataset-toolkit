"""Checks that a set of boxes can fail. Pure: no disk, no CLI, no OpenCV.

Two families live here, and keeping them apart is the point.

The structural checks apply to any YOLO dataset: a coordinate outside 0..1 is
wrong whatever the classes mean, and nobody has to declare that.

The relation checks are the dataset's own conventions - "every person has a
head or a helmet" - and those cannot be guessed. They are declared in a rules
file and only run when one is given, because applying one dataset's
conventions to another measures the distance between the two, not the quality
of either.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..core.boxes import AnnotationError, Box

# A box smaller than this is almost certainly a stray click, not an object.
MIN_AREA = 1e-6

# Two boxes of the same class overlapping this much are the same object twice.
DUPLICATE_IOU = 0.9

# Default for `exclusive`, when the rules file does not say.
DEFAULT_EXCLUSIVE_IOU = 0.5


@dataclass(frozen=True, slots=True)
class Finding:
    """One problem found in one image."""

    rule: str
    detail: str


# --- how "this box belongs to that box" is decided ------------------------


def _aligned(part: Box, whole: Box) -> bool:
    """Lined up horizontally with `whole`, and touching it.

    The default, because it survives real annotation. Area overlap fails for
    anything worn on top of something else - a helmet sits above the head and
    gets drawn poking past the body, so half of it can lie outside the person
    while it plainly belongs to them. Its horizontal position does not move.
    """
    left, _, right, _ = whole.bounds
    return left <= part.x_center <= right and part.intersection(whole) > 0


def _inside(part: Box, whole: Box) -> bool:
    """`part`'s center point falls within `whole`. Stricter than aligned."""
    left, top, right, bottom = whole.bounds
    return left <= part.x_center <= right and top <= part.y_center <= bottom


def _overlapping(part: Box, whole: Box) -> bool:
    """The two boxes share any area at all. The loosest of the three."""
    return part.intersection(whole) > 0


ASSOCIATIONS = {"aligned": _aligned, "inside": _inside, "overlapping": _overlapping}
DEFAULT_ASSOCIATION = "aligned"


# --- the rules themselves -------------------------------------------------


@dataclass(frozen=True, slots=True)
class Relation:
    """Every box of `subject` must relate to one of `others`.

    `holds` says which way round the geometry goes, and it matters because
    the association test is not symmetric. "A person contains a head" and "a
    head sits within a person" describe the same picture but check different
    arguments, so the file has to be explicit about which is the part and
    which is the whole.
    """

    subject: str
    others: tuple[str, ...]
    holds: str  # "contains" or "within"
    name: str


@dataclass(frozen=True, slots=True)
class Exclusive:
    """Boxes of these classes must not describe the same object."""

    classes: tuple[str, ...]
    iou: float
    name: str


@dataclass(frozen=True, slots=True)
class RuleSet:
    """What a rules file says, before it meets a dataset."""

    relations: tuple[Relation, ...] = ()
    exclusive: tuple[Exclusive, ...] = ()
    association: str = DEFAULT_ASSOCIATION

    @classmethod
    def from_file(cls, path: Path) -> "RuleSet":
        document = yaml.safe_load(path.read_text()) or {}
        if not isinstance(document, dict):
            raise AnnotationError(f"{path}: esperava um mapa no topo do arquivo")
        return cls.from_document(document, source=str(path))

    @classmethod
    def from_document(cls, document: dict[str, Any], source: str = "rules") -> "RuleSet":
        association = document.get("association", DEFAULT_ASSOCIATION)
        if association not in ASSOCIATIONS:
            known = ", ".join(sorted(ASSOCIATIONS))
            raise AnnotationError(f"{source}: association {association!r} não existe (use: {known})")

        relations: list[Relation] = []
        exclusive: list[Exclusive] = []

        entries = document.get("rules")
        if not entries:
            raise AnnotationError(f"{source}: nenhuma regra em 'rules'")

        for position, entry in enumerate(entries, start=1):
            where = f"{source}: regra {position}"
            if not isinstance(entry, dict):
                raise AnnotationError(f"{where}: esperava um mapa")

            if "class" in entry:
                subject = entry["class"]
                holds = next((key for key in ("contains_any", "within_any") if key in entry), None)
                if holds is None:
                    raise AnnotationError(
                        f"{where}: 'class' precisa de 'contains_any' ou 'within_any'"
                    )
                others = entry[holds]
                if isinstance(others, str):
                    others = [others]
                if not others:
                    raise AnnotationError(f"{where}: '{holds}' está vazio")
                relations.append(
                    Relation(
                        subject=subject,
                        others=tuple(others),
                        holds="contains" if holds == "contains_any" else "within",
                        name=entry.get("name") or f"{subject}-sem-{'-ou-'.join(others)}",
                    )
                )
            elif "exclusive" in entry:
                classes = entry["exclusive"]
                if not isinstance(classes, list) or len(classes) < 2:
                    raise AnnotationError(f"{where}: 'exclusive' precisa de ao menos duas classes")
                exclusive.append(
                    Exclusive(
                        classes=tuple(classes),
                        iou=float(entry.get("iou", DEFAULT_EXCLUSIVE_IOU)),
                        name=entry.get("name") or f"{'-e-'.join(classes)}-juntos",
                    )
                )
            else:
                raise AnnotationError(f"{where}: esperava 'class' ou 'exclusive'")

        return cls(tuple(relations), tuple(exclusive), association)

    def resolve(self, class_names: Sequence[str]) -> "ResolvedRules":
        """Turn class names into ids for this dataset, or say what is missing.

        Unknown class names are an error, not a skipped check: passing rules
        written for another dataset should say so, not quietly validate
        nothing and report success.
        """
        index = {name.strip(): position for position, name in enumerate(class_names)}

        def ids(names: Sequence[str], where: str) -> tuple[int, ...]:
            missing = [name for name in names if name not in index]
            if missing:
                known = ", ".join(class_names)
                raise AnnotationError(
                    f"{where}: classe {', '.join(repr(m) for m in missing)}"
                    f" não existe neste dataset (tem: {known})"
                )
            return tuple(index[name] for name in names)

        return ResolvedRules(
            relations=tuple(
                (rule, ids([rule.subject], rule.name)[0], ids(rule.others, rule.name))
                for rule in self.relations
            ),
            exclusive=tuple((rule, ids(rule.classes, rule.name)) for rule in self.exclusive),
            associate=ASSOCIATIONS[self.association],
        )


@dataclass(frozen=True, slots=True)
class ResolvedRules:
    """The same rules, with class names already turned into ids."""

    relations: tuple[tuple[Relation, int, tuple[int, ...]], ...]
    exclusive: tuple[tuple[Exclusive, tuple[int, ...]], ...]
    associate: Any


# --- running them ---------------------------------------------------------


def check_image(
    boxes: Sequence[Box],
    class_names: Sequence[str],
    rules: ResolvedRules | None = None,
) -> list[Finding]:
    """Every finding for one image's boxes."""
    findings = list(_check_structure(boxes, class_names))
    findings.extend(_check_duplicates(boxes, class_names))
    if rules is not None:
        findings.extend(_check_relations(boxes, class_names, rules))
    return findings


def _check_structure(boxes: Sequence[Box], class_names: Sequence[str]) -> Iterator[Finding]:
    for position, box in enumerate(boxes, start=1):
        where = f"caixa {position}"

        if not 0 <= box.class_id < len(class_names):
            yield Finding("classe-desconhecida", f"{where}: id {box.class_id} não existe em data.yaml")

        if box.width <= 0 or box.height <= 0:
            yield Finding("caixa-degenerada", f"{where}: largura ou altura zero/negativa")
        elif box.area < MIN_AREA:
            yield Finding("caixa-degenerada", f"{where}: área {box.area:.2e}, provável clique perdido")

        left, top, right, bottom = box.bounds
        if left < -1e-6 or top < -1e-6 or right > 1 + 1e-6 or bottom > 1 + 1e-6:
            yield Finding(
                "fora-da-imagem",
                f"{where}: extrapola a borda ({left:.3f}, {top:.3f}) a ({right:.3f}, {bottom:.3f})",
            )


def _check_duplicates(boxes: Sequence[Box], class_names: Sequence[str]) -> Iterator[Finding]:
    for first in range(len(boxes)):
        for second in range(first + 1, len(boxes)):
            a, b = boxes[first], boxes[second]
            if a.class_id == b.class_id and a.iou(b) >= DUPLICATE_IOU:
                yield Finding(
                    "caixa-duplicada",
                    f"caixas {first + 1} e {second + 1}: mesmo {_name(a.class_id, class_names)},"
                    f" IoU {a.iou(b):.2f}",
                )


def _check_relations(
    boxes: Sequence[Box], class_names: Sequence[str], rules: ResolvedRules
) -> Iterator[Finding]:
    for rule, subject_id, other_ids in rules.relations:
        subjects = [box for box in boxes if box.class_id == subject_id]
        others = [box for box in boxes if box.class_id in other_ids]

        for position, subject in enumerate(subjects, start=1):
            # The association test takes (part, whole), so `holds` decides
            # which side the subject goes on.
            found = any(
                rules.associate(other, subject)
                if rule.holds == "contains"
                else rules.associate(subject, other)
                for other in others
            )
            if not found:
                yield Finding(
                    rule.name,
                    f"{rule.subject} {position}: sem {' nem '.join(rule.others)} associado",
                )

    for rule, class_ids in rules.exclusive:
        members = [box for box in boxes if box.class_id in class_ids]
        for first in range(len(members)):
            for second in range(first + 1, len(members)):
                a, b = members[first], members[second]
                if a.class_id != b.class_id and a.iou(b) >= rule.iou:
                    yield Finding(
                        rule.name,
                        f"{_name(a.class_id, class_names)} e {_name(b.class_id, class_names)}"
                        f" no mesmo objeto (IoU {a.iou(b):.2f})",
                    )


def _name(class_id: int, class_names: Sequence[str]) -> str:
    if 0 <= class_id < len(class_names):
        return class_names[class_id]
    return f"class_{class_id}"
