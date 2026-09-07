"""Checks that a set of boxes can fail. Pure: no disk, no CLI, no OpenCV.

Two families live here. The structural checks apply to any YOLO dataset — a
coordinate outside 0..1 is wrong no matter what the classes mean. The rule
checks encode ANNOTATION_GUIDE.md, so they only run when the dataset actually
has the classes those rules talk about.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from .boxes import Box

# A box smaller than this is almost certainly a stray click, not an object.
MIN_AREA = 1e-6

# Two boxes of the same head disagreeing about whether it is covered.
CONFLICT_IOU = 0.5

# Two boxes of the same class overlapping this much are the same object twice.
DUPLICATE_IOU = 0.9


@dataclass(frozen=True, slots=True)
class Finding:
    """One problem found in one image."""

    rule: str
    detail: str


@dataclass(frozen=True, slots=True)
class Roles:
    """Which class ids play which role in the guide's rules.

    Resolved from the dataset's own names, so a dataset that calls them
    something else simply skips the rule checks instead of misfiring.
    """

    person: int | None = None
    head: int | None = None
    helmet: int | None = None
    vest: int | None = None

    @classmethod
    def from_names(cls, class_names: Sequence[str]) -> "Roles":
        index = {name.strip().lower(): position for position, name in enumerate(class_names)}
        return cls(
            person=index.get("person"),
            head=index.get("head"),
            helmet=index.get("helmet"),
            vest=index.get("reflective-vest", index.get("vest")),
        )


def check_image(boxes: Sequence[Box], class_names: Sequence[str], roles: Roles) -> list[Finding]:
    """Every finding for one image's boxes."""
    findings = list(_check_structure(boxes, class_names))
    findings.extend(_check_duplicates(boxes, class_names))
    findings.extend(_check_rules(boxes, roles))
    return findings


def _check_structure(boxes: Sequence[Box], class_names: Sequence[str]) -> Iterator[Finding]:
    for position, box in enumerate(boxes):
        where = f"caixa {position + 1}"

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


def _check_rules(boxes: Sequence[Box], roles: Roles) -> Iterator[Finding]:
    people = [box for box in boxes if box.class_id == roles.person]
    heads = [box for box in boxes if box.class_id == roles.head]
    helmets = [box for box in boxes if box.class_id == roles.helmet]
    vests = [box for box in boxes if box.class_id == roles.vest]

    # Regra 3: toda person tem pelo menos um head ou um helmet. A associação
    # é pelo centro, não por área: um capacete é desenhado transbordando o
    # topo do corpo com frequência, e continua sendo daquela pessoa.
    if roles.person is not None and (roles.head is not None or roles.helmet is not None):
        for position, person in enumerate(people, start=1):
            if not any(_worn_by(part, person) for part in heads + helmets):
                yield Finding("person-sem-cabeca", f"person {position}: sem head nem helmet dentro")

    # Regras 1 e 3: uma cabeça implica uma pessoa. Capacete solto é permitido
    # pela regra 5, cabeça solta não tem caso legítimo.
    if roles.person is not None and roles.head is not None:
        for position, head in enumerate(heads, start=1):
            if not any(_worn_by(head, person) for person in people):
                yield Finding("head-sem-person", f"head {position}: nenhuma person em volta")

    # Regra 5: colete só conta quando vestido.
    if roles.person is not None and roles.vest is not None:
        for position, vest in enumerate(vests, start=1):
            if not any(_worn_by(vest, person) for person in people):
                yield Finding("colete-sem-person", f"reflective-vest {position}: não está em ninguém")

    # As classes são mutuamente exclusivas: a mesma cabeça não é as duas.
    if roles.head is not None and roles.helmet is not None:
        for position, head in enumerate(heads, start=1):
            for helmet in helmets:
                if head.iou(helmet) >= CONFLICT_IOU:
                    yield Finding(
                        "head-e-helmet-juntos",
                        f"head {position}: sobrepõe um helmet (IoU {head.iou(helmet):.2f})",
                    )
                    break


def _worn_by(part: Box, person: Box) -> bool:
    """Whether `part` belongs to `person`.

    Not area overlap, and not the part's center being inside the person
    either: a helmet sits on top of the head and gets drawn poking above the
    body, so on real annotations both tests reject helmets that plainly
    belong to someone. What holds is that the part is lined up horizontally
    with the person and touching them.
    """
    left, _, right, _ = person.bounds
    return left <= part.x_center <= right and part.intersection(person) > 0


def _name(class_id: int, class_names: Sequence[str]) -> str:
    if 0 <= class_id < len(class_names):
        return class_names[class_id]
    return f"class_{class_id}"
