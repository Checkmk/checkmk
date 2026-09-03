#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""GUI-only "Relations" between hosts (management boards <-> OS hosts).

This is a pure Setup/GUI feature. It links a management-board host to the OS hosts it manages
(and vice versa) so both sides are navigable, and it is surfaced in the monitoring without ever
changing how a host is checked or notified.

A relation is stored in the ``relations`` host attribute of **both** hosts, each from its own
side. That is what lets every host answer what it is related to by looking at itself: the reverse
links of a host would otherwise be the forward links of every *other* host, and finding them
would mean loading every folder's ``hosts.mk``.

:func:`resolve_all_relations` derives the reverse of every stored half anyway, so a pair
collapses into one relation per side - and a half whose counterpart row was lost still reaches
both hosts.
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Literal, Protocol

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.utils.host_relation_kinds import (
    DirectedRelationKind,
    known_relations,
    RELATION_KINDS,
)
from cmk.gui.utils.host_relations import (
    parse_relations_value,
    RelationDirection,
    RelationLink,
    RelationsValue,
    ResolvedRelation,
    reverse_direction,
)
from cmk.gui.watolib.host_attributes import HostAttributes

_LOGGER = logger.getChild("host_relations")


class RelatedHost(Protocol):
    """What :func:`resolve_all_relations` reads off a host - no more than this.

    Spelled out so the resolver can be exercised without building a whole folder tree, and so the
    contract is in the signature rather than in a cast at the call site.
    """

    @property
    def attributes(self) -> HostAttributes: ...

    def name(self) -> HostName: ...

    def site_id(self) -> SiteId: ...


ResolvedRelations = dict[HostName, list[ResolvedRelation]]


@dataclass(frozen=True)
class RelationConflict:
    """What speaks against storing a link, as a value rather than as its wording.

    Comparable, so that an edit can tell the contradictions it introduces from the ones that were
    already stored, without that answer hanging on how a sentence happens to read.
    """

    reason: Literal["self_link", "contradicting_directions", "duplicate"]
    host: HostName | None = None
    kind_id: str | None = None

    def message(self) -> str:
        match self.reason:
            case "self_link":
                return _("A host cannot be linked to itself.")
            case "contradicting_directions":
                assert self.kind_id is not None
                kind = RELATION_KINDS[self.kind_id]
                # Only a directed kind has two ends to contradict each other; a symmetric one
                # stores the same direction on both hosts and can never get here.
                assert isinstance(kind, DirectedRelationKind)
                return _(
                    "This host is linked to '%(host)s' both as its '%(end)s' and as its "
                    "'%(other_end)s'. A host can only sit at one end of a relation."
                ) % {
                    "host": self.host,
                    "end": kind.parent.noun,
                    "other_end": kind.child.noun,
                }
            case "duplicate":
                return _("'%(host)s' is linked more than once. Remove the duplicate.") % {
                    "host": self.host
                }


def relation_conflicts(
    links: Sequence[RelationLink], owner: HostName
) -> Sequence[RelationConflict]:
    """Everything that speaks against storing ``links`` on ``owner``, in reporting order.

    Only what the value says about *this* host; those contradictions are rejected on save. What
    the counterpart stores, and whether it still exists, is reported instead (see
    :func:`cmk.gui.watolib.builtin_attributes.validate_host_relations`): rejecting it here would
    make one host unsavable because someone else broke the other.

    Links are grouped per relation, not per linked host: two links naming the same host are a
    contradiction only as the two ends of the *same* relation. Only the kinds this version knows
    are grouped - what a relation of a later version says about itself is not for this one to
    judge, and it could not word the refusal anyway. Linking a host to itself is refused whatever
    the kind: that is wrong without knowing what the relation means.
    """
    conflicts: list[RelationConflict] = []

    if any(link["host"] == owner for link in links):
        conflicts.append(RelationConflict(reason="self_link"))

    directions_by_relation: dict[tuple[HostName, str], list[RelationDirection]] = {}
    for link in known_relations(links):
        if link["host"] == owner:
            continue
        directions_by_relation.setdefault((link["host"], link["kind"]), []).append(
            link["direction"]
        )

    for (host_name, kind_id), directions in directions_by_relation.items():
        distinct = set(directions)
        if len(distinct) > 1:
            conflicts.append(
                RelationConflict(reason="contradicting_directions", host=host_name, kind_id=kind_id)
            )
        if len(directions) > len(distinct):
            conflicts.append(RelationConflict(reason="duplicate", host=host_name, kind_id=kind_id))

    return conflicts


def relations_or_user_error(raw: object) -> RelationsValue:
    """The links of a stored ``relations`` value, as a user error if it cannot be read at all."""
    try:
        return parse_relations_value(raw)
    except ValueError as exc:
        raise MKUserError(
            None, _("The relations of this host are malformed: %(error)s") % {"error": exc}
        ) from exc


def resolve_all_relations(all_hosts: Mapping[HostName, RelatedHost]) -> ResolvedRelations:
    """Resolve every host's relations (both directions) into concrete host names.

    Both halves of a relation are stored, so one pass over the ``relations`` attribute of every
    host sees every relation twice. The reverse of each half is derived anyway: that is what makes
    a hand written ``hosts.mk`` holding only one half still materialize on both sides.

    Reads each host's *own* attributes, not its effective ones. That is deliberate - a
    folder-level value would mean every host in the folder pointing at the same board - and it is
    only safe because the attribute is not inheritable
    (``HostAttributeRelations.show_in_folder() -> False``).

    The result maps each host to the list of hosts related to it, with the end that host sits at
    towards each of them - the same reading as the stored links, so the materialized value and
    the one in "hosts.mk" say the same thing. Duplicates are removed, so a stored pair collapses
    into one relation per side. Hosts without relations are omitted.
    """
    # A relation identifies itself, so a dict keyed by it is the set of them that keeps the
    # order they were resolved in.
    resolved: defaultdict[HostName, dict[ResolvedRelation, None]] = defaultdict(dict)
    # Asked once per related host rather than once per link: site_id() walks the folder chain up
    # to a file system check, and a board with many OS hosts is one host holding many links.
    sites: dict[HostName, str] = {}

    def _site_of(host: RelatedHost) -> str:
        if (site := sites.get(name := host.name())) is None:
            site = sites[name] = str(host.site_id())
        return site

    def _drop_reason(owner: HostName, other: HostName) -> str | None:
        if owner == other:
            return "self-reference"
        if other not in all_hosts:
            return "related host does not exist"
        return None

    def _add(
        owner: HostName, kind_id: str, direction: RelationDirection, other: RelatedHost
    ) -> None:
        relation = ResolvedRelation(
            kind=kind_id, direction=direction, host=other.name(), site=_site_of(other)
        )
        resolved[owner][relation] = None

    def _unknown_direction(owner: HostName, direction: str) -> None:
        _LOGGER.debug(
            "Relation of host %(owner)r dropped: direction %(direction)r is unknown to this"
            " version.",
            {"owner": owner, "direction": direction},
        )

    def _unknown_kind(owner: HostName, link: RelationLink) -> None:
        _LOGGER.debug(
            "Relation of host %(owner)r dropped: this version does not know a %(kind)r relation"
            " with a %(direction)r end.",
            {"owner": owner, "kind": link["kind"], "direction": link["direction"]},
        )

    for host_name, host in all_hosts.items():
        try:
            parsed = parse_relations_value(
                host.attributes.get("relations", []),
                on_unknown_direction=partial(_unknown_direction, host_name),
            )
        except ValueError as exc:
            # Only a hand written "hosts.mk" gets here, and a debug line would hide it from
            # whoever wonders where their relations went.
            _LOGGER.warning(
                "Skipping malformed 'relations' attribute of host %(host)r: %(error)s",
                {"host": host_name, "error": exc},
            )
            continue
        for link in known_relations(parsed, on_unknown=partial(_unknown_kind, host_name)):
            if (reason := _drop_reason(host_name, link["host"])) is not None:
                _LOGGER.debug(
                    "Relation %(owner)r -> %(other)r (%(kind)s/%(direction)s) dropped: %(reason)s.",
                    {
                        "owner": host_name,
                        "other": link["host"],
                        "kind": link["kind"],
                        "direction": link["direction"],
                        "reason": reason,
                    },
                )
                continue
            other = all_hosts[link["host"]]
            _add(host_name, link["kind"], link["direction"], other)
            _add(other.name(), link["kind"], reverse_direction(link["direction"]), host)

    return {owner: list(relations) for owner, relations in resolved.items()}
