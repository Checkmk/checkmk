#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The kinds of relation two hosts can have, and how each end of one is worded.

A kind is an object with its readings as fields, so the one table below decides what the host
dialog offers, what a contradiction message says, and what the monitoring calls a related host. A
further kind is one more entry here; nothing else enumerates them.

Only the ids of a kind and of a direction are stored (see :mod:`cmk.gui.utils.host_relations`),
so the wording stays free to change and to be translated. That is also why this is a module of
its own: the wording is lazily translated and needs ``_l``, which the stdlib-only wire-format
module below it cannot import.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from cmk.gui.i18n import _l
from cmk.gui.utils.host_relations import RelationDirection, RelationLink
from cmk.web.utils.speaklater import LazyString


@dataclass(frozen=True)
class RelationEnd:
    """How the host sitting at one end of a relation is worded.

    Both readings are needed because the GUI uses both: a row of the host dialog is a sentence
    about the host being edited, while a card in the monitoring and the message refusing a
    contradiction name the host itself.
    """

    row: LazyString
    """The dialog row, read towards the related host: "is management board of"."""

    noun: LazyString
    """The host sitting at this end: "Management board"."""


@dataclass(frozen=True)
class DirectedRelationKind:
    """A relation that reads differently from each side.

    ``parent`` is the managing, standing-for end and ``child`` the one it stands for.
    ``end(direction).noun`` names the host that *sits* at ``direction`` - so the storing host of a
    link calls itself ``end(link["direction"]).noun`` and its counterpart
    ``end(reverse_direction(link["direction"])).noun``.
    """

    id: str
    parent: RelationEnd
    child: RelationEnd

    def __post_init__(self) -> None:
        _validate_kind_id(self.id)

    def directions(self) -> Sequence[RelationDirection]:
        return ("parent", "child")

    def end(self, direction: RelationDirection) -> RelationEnd:
        match direction:
            case "parent":
                return self.parent
            case "child":
                return self.child
            case "symmetric":
                raise ValueError(f"Relation kind {self.id!r} has no symmetric end.")


@dataclass(frozen=True)
class SymmetricRelationKind:
    """A relation that reads the same from both sides, like "is peer of".

    Both hosts store the same direction, so there is one wording rather than two.
    """

    id: str
    peer: RelationEnd

    def __post_init__(self) -> None:
        _validate_kind_id(self.id)

    def directions(self) -> Sequence[RelationDirection]:
        return ("symmetric",)

    def end(self, direction: RelationDirection) -> RelationEnd:
        if direction != "symmetric":
            raise ValueError(f"Relation kind {self.id!r} has no {direction!r} end.")
        return self.peer


RelationKind = DirectedRelationKind | SymmetricRelationKind


def _validate_kind_id(kind_id: str) -> None:
    """A kind id ends up in an element name of the host dialog, which has to be an identifier."""
    if not kind_id.isidentifier():
        raise ValueError(f"Relation kind id must be an identifier: {kind_id!r}")


#: Every kind of relation this version knows, by id. The one place a further kind goes: the dialog
#: rows, the reverse mapping and the grouping of contradictions all follow from it.
RELATION_KINDS: Final[Mapping[str, RelationKind]] = {
    kind.id: kind
    for kind in (
        DirectedRelationKind(
            id="management",
            parent=RelationEnd(row=_l("is management board of"), noun=_l("Management board")),
            child=RelationEnd(row=_l("is OS host of"), noun=_l("OS host")),
        ),
    )
}


def kind_accepts(kind_id: str, direction: RelationDirection) -> bool:
    """Whether this version knows ``kind_id`` and that kind has such an end.

    Both halves are the same question for a reader: a link it cannot place is one it has to skip,
    whether the kind is from a later version or the direction does not belong to the kind it
    names.
    """
    kind = RELATION_KINDS.get(kind_id)
    return kind is not None and direction in kind.directions()


def known_relations(
    links: Iterable[RelationLink],
    *,
    on_unknown: Callable[[RelationLink], None] = lambda _link: None,
) -> list[RelationLink]:
    """The links whose kind and direction this version can place.

    The others are reported rather than rejected: a link of a later version must not cost a host
    the rest of its relations, the same forward-compatibility rule
    :func:`cmk.gui.utils.host_relations.parse_relations_value` applies to the direction.
    """
    known = []
    for link in links:
        if kind_accepts(link["kind"], link["direction"]):
            known.append(link)
        else:
            on_unknown(link)
    return known
