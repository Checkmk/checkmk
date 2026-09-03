#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The two forms a host relation takes, and the codecs for both.

A relation is *stored* on a host as a :class:`RelationLink` in its ``relations`` attribute, and
*materialized* into the monitoring core as a :class:`ResolvedRelation` in the ``_RELATIONS``
custom host variable. Setup writes both; the monitoring reads only the second, from whatever a
site's core reports - possibly a site whose configuration was written by another Checkmk version.

Both are formats rather than logic, and this module is their only definition: the directions a
host can sit at, the macro name, and the parsers. It knows *that* a link names a kind of relation,
not *which* kinds exist - that is :mod:`cmk.gui.utils.host_relation_kinds`, which carries
translatable wording and therefore cannot live this far down. A reader that has to tell a known
kind from one a later version wrote asks that module.

The monitoring domain deliberately knows nothing about Setup and Setup knows nothing about
Livestatus, so the shared vocabulary lives in a home that belongs to neither (see
:mod:`cmk.gui.watolib.host_relations` for what Setup does with it).
"""

import dataclasses
import json
from collections.abc import Callable, Iterator, Sequence
from typing import get_args, Literal, TypedDict, TypeGuard, TypeIs

from cmk.ccc.hostaddress import HostName

#: Which end of a relation a host sits at. ``parent`` is the managing, standing-for side and
#: ``child`` the one it stands for; ``symmetric`` is both ends of a relation that reads the same
#: from either side ("is peer of"). Unrelated to a host's ``parents`` attribute, which is about
#: network reachability and has nothing to do with this.
#:
#: These strings sit in every "hosts.mk" and in every core configuration that holds a relation, so
#: they name the *structure* of a relation rather than the words the GUI happens to use for it:
#: which product vocabulary is right for a management board - BMC, service processor, management
#: interface - is a wording question and may well be settled differently later, whereas one host
#: managing the other out of band is not. Renaming a title in the dialog must therefore never
#: reach this line; renaming this line is a migration of every installation that already stores a
#: relation. The same holds for the kind ids in :mod:`cmk.gui.utils.host_relation_kinds`.
RelationDirection = Literal["parent", "child", "symmetric"]

_RELATION_DIRECTIONS: frozenset[str] = frozenset(get_args(RelationDirection))


def _is_relation_direction(value: object) -> TypeIs[RelationDirection]:
    """Whether a value read from somewhere else names a direction this Checkmk version knows.

    The ``isinstance`` is not redundant: ``value in frozenset(...)`` raises ``TypeError`` for an
    unhashable value, and :func:`parse_resolved_relations` is documented to survive exactly such
    input.
    """
    return isinstance(value, str) and value in _RELATION_DIRECTIONS


def reverse_direction(direction: RelationDirection) -> RelationDirection:
    """The same relation seen from the other host: an OS host's parent is its management board.

    A symmetric relation reads the same from either side, so it is its own reverse.
    """
    match direction:
        case "parent":
            return "child"
        case "child":
            return "parent"
        case "symmetric":
            return "symmetric"


def _is_nonempty_str(value: object) -> TypeGuard[str]:
    """An empty name is as unusable as a missing one, and would be looked up as if it were real."""
    return isinstance(value, str) and bool(value)


class RelationLink(TypedDict):
    """One relation as it is stored in a host's ``relations`` attribute.

    ``kind`` names the relation and ``direction`` the end the *storing* host sits at, so a link
    reads left to right the way its row in the host dialog does: "this host is the OS host of
    ``host``". One entry per linked host, mirroring the one row per relation of the dialog. Both
    halves of a relation are stored - each host holds the link from its own side (see
    :func:`reverse_direction`), so no host has to look at any other one to know what it is
    related to.

    ``kind`` is a plain ``str`` here rather than one of the ids this version knows: a link may
    well name a kind a later version introduced, and a reader has to be able to hold it before it
    can decide to skip it (see :func:`cmk.gui.utils.host_relation_kinds.known_relations`).

    :class:`ResolvedRelation`, the materialized form, reads the same way, so a relation says the
    same thing in "hosts.mk" and in the monitoring core.
    """

    kind: str
    direction: RelationDirection
    host: HostName


RelationsValue = list[RelationLink]


def parse_relations_value(
    raw: object, *, on_unknown_direction: Callable[[str], None] = lambda _direction: None
) -> RelationsValue:
    """Validate and normalize the raw (JSON-decoded) ``relations`` attribute value.

    Raises ``ValueError`` on structurally invalid input - which includes an unusable host name,
    because that is what every reader of a link would trip over next.

    A link naming a direction this version does not know is *skipped* instead: it is not a broken
    value but one a later version wrote, and everything that writes the attribute re-states the
    whole list from what it parsed (see
    :meth:`cmk.gui.watolib.hosts_and_folders.Host.set_relations_about`). Raising would therefore
    turn one unreadable row into a host without any relations at all on its next save. A skip is
    still a relation the caller will not see, so ``on_unknown_direction`` is called with the
    direction for callers that have somewhere to report it - this module has no opinion on where
    that is. The skip happens *before* the host name is validated, so a row of a later version
    never fails on a field this version reads more strictly.

    An unknown *kind* is not skipped here: this module does not know which kinds exist. That
    answer, and the same forward compatibility for it, live in
    :mod:`cmk.gui.utils.host_relation_kinds`.

    The forward compatibility stops at the *fields* of a link: one is rebuilt from the three this
    version knows, so a field a later version added to it does not survive being read and written
    here. Skipping cannot help there - a link this version can place is one it also re-states.
    """
    if not isinstance(raw, list):
        raise ValueError("Relations must be a list of links.")

    links: RelationsValue = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("Each relation link must be a mapping.")
        kind = entry.get("kind")
        if not _is_nonempty_str(kind):
            raise ValueError(f"Invalid relation kind: {kind!r}")
        direction = entry.get("direction")
        if not isinstance(direction, str):
            raise ValueError(f"Invalid relation direction: {direction!r}")
        if not _is_relation_direction(direction):
            on_unknown_direction(direction)
            continue
        host = entry.get("host")
        if not _is_nonempty_str(host):
            raise ValueError("A relation link requires a host name.")
        # HostNameValidationError is a ValueError, so an unusable name is reported like any other
        # structural defect instead of escaping to whoever reads the link later.
        links.append({"kind": kind, "direction": direction, "host": HostName.parse(host)})
    return links


def relations_or_empty(raw: object) -> RelationsValue:
    """The links of a ``relations`` attribute value, or none at all if it is malformed.

    For readers that have nothing to say about a broken value. A malformed one is rejected when a
    host is saved, so a stored one can only come from a hand written ``hosts.mk``; use
    :func:`parse_relations_value` where that has to be reported.
    """
    try:
        return parse_relations_value(raw)
    except ValueError:
        return []


def referenced_host_names(links: Sequence[RelationLink]) -> set[HostName]:
    """All host names referenced by the links (for cross-host validation on save)."""
    return {link["host"] for link in links}


def relation_key(link: RelationLink) -> tuple[str, RelationDirection, HostName]:
    """What makes a link the same link, for comparing two sets of them."""
    return link["kind"], link["direction"], link["host"]


#: The custom host variable Setup writes, via a generated ``explicit_host_conf`` file.
RELATIONS_MACRO = "_RELATIONS"

#: The same variable as Livestatus reports it: it strips the leading underscore of a custom
#: variable's name, so a reader of ``custom_variables`` has to ask for it without one.
RELATIONS_CUSTOM_VARIABLE = RELATIONS_MACRO.removeprefix("_")


@dataclasses.dataclass(frozen=True)
class ResolvedRelation:
    """One relation of one host, as it is materialized into the monitoring core.

    ``direction`` is the end *this* host sits at towards ``host``, the same reading as the stored
    :class:`RelationLink` it comes from; ``host`` is the related host and ``site`` the site
    monitoring it. The site travels with the relation because only the central site knows where
    every host is monitored; it lets a reader query the counterpart's site directly instead of
    asking every site whether it knows the name. A reader that wants to label the related host -
    "this one is my management board" - turns the direction with :func:`reverse_direction`.

    The host and the site are plain strings: a reader parses them out of a value it did not write,
    and turning them into a ``HostName`` or a ``SiteId`` is its own business.
    """

    kind: str
    direction: RelationDirection
    host: str
    site: str


def dump_resolved_relations(relations: Sequence[ResolvedRelation]) -> str:
    # vars() rather than dataclasses.asdict(): that walks the recursive deep-copy machinery for
    # what is four strings, and this runs for every relation on every activation.
    return json.dumps([vars(relation) for relation in relations])


def parse_resolved_relations(raw: str | None) -> Iterator[ResolvedRelation]:
    """Yield the relations a materialized value holds, skipping whatever does not belong.

    Be defensive: the value comes from a core the reader does not control, so a single bad entry
    must never break the page showing it. Whether the kind is one this version knows is not asked
    here - see :func:`cmk.gui.utils.host_relation_kinds.known_relations`.
    """
    if not raw:
        return
    try:
        entries = json.loads(raw)
    except ValueError:
        return
    if not isinstance(entries, list):
        return
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind")
        direction = entry.get("direction")
        host = entry.get("host")
        site = entry.get("site")
        if (
            _is_nonempty_str(kind)
            and _is_relation_direction(direction)
            and _is_nonempty_str(host)
            and _is_nonempty_str(site)
        ):
            yield ResolvedRelation(kind=kind, direction=direction, host=host, site=site)
