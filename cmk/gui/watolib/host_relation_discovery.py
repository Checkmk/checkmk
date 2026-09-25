#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Find the relations the hosts in Setup already show.

Relations are stored on both hosts of a pair, which is why every bulk route into the
``relations`` attribute is closed (see
:class:`cmk.gui.watolib.builtin_attributes.HostAttributeRelations`). Onboarding a fleet
still needs one, and this is the shape that keeps the invariant: read the evidence that is
already in the configuration, propose what it speaks for, and let the mirroring primitives
of :mod:`cmk.gui.watolib.hosts_and_folders` do the writing for the proposals the user
accepts.

Discovery rather than a rule, the way services are found rather than configured: the two
hosts of a relation say so themselves - a board named after the host it sits in, or a
label the CMDB wrote on both - and a user who has to describe that in regular expressions
is doing the work the configuration has already done.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import assert_never, Final

from cmk.ccc.hostaddress import HostName
from cmk.gui.i18n import _
from cmk.gui.utils.host_relation_kinds import (
    is_name_token,
    kind_accepts,
    NAME_SEPARATORS,
    RELATION_KINDS,
    RelationKind,
)
from cmk.gui.utils.host_relations import RelationDirection, reverse_direction
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.host_relations import relation_choice_name
from cmk.ruleset_matcher.labels import Labels

#: What a host name puts between the parts of its first label.
_SEPARATORS: Final = "-_"

#: Everything a name is made of, the domain included: "srv-01.ilo.example.com" is five parts.
_PARTS: Final = re.compile(rf"[{re.escape(NAME_SEPARATORS)}]")

#: A word as the last, respectively the first, part of the first label: "srv-01-ilo",
#: "ilo-srv-01". Anchored, so that "ilonka" and "srv-01-ilo2" carry no word "ilo" at all.
_WORD_AT_END: Final = re.compile(rf"^(?P<base>.+)[{_SEPARATORS}](?P<word>[^{_SEPARATORS}]+)$")
_WORD_AT_START: Final = re.compile(rf"^(?P<word>[^{_SEPARATORS}]+)[{_SEPARATORS}](?P<base>.+)$")


def _placements(name: str) -> list[tuple[str, str]]:
    """Every place a relation word can sit in ``name``, with the name taking it out leaves.

    * a label of its own - ``"ilo.srv-01"``, and the management domain
      ``"srv-01.ilo.example.com"`` next to ``"srv-01.example.com"``
    * the last or first part of the first label - ``"srv-01-ilo"``, ``"ilo-srv-01"``

    The one place the scan and the suggestions read names by, so they cannot disagree about
    what a name carries. A domain is kept, because it belongs to the other host too.
    """
    labels = name.split(".")
    found = (
        [(label, ".".join(labels[:at] + labels[at + 1 :])) for at, label in enumerate(labels)]
        if len(labels) > 1
        else []
    )
    head, dot, domain = name.partition(".")
    for pattern in (_WORD_AT_END, _WORD_AT_START):
        if (match := pattern.match(head)) is not None:
            found.append((match["word"], match["base"] + dot + domain))
    return found


@dataclass(frozen=True)
class SharedLabel:
    """Hosts carrying the same value in this host label belong together."""

    name: str


@dataclass(frozen=True)
class SharedAttribute:
    """Hosts carrying the same value in this custom host attribute belong together."""

    name: str


#: What to read on top of the host names, or ``None`` for the names alone.
SharedValue = SharedLabel | SharedAttribute | None


@dataclass(frozen=True)
class NameWords:
    """The host at the deciding end carries one of these words in its name.

    The one marker that also pairs the hosts: taking the word back out of a name gives the
    host at the other end, so a fleet named this way needs nothing else.
    """

    words: Sequence[str]


@dataclass(frozen=True)
class MarkedValue:
    """The host at the deciding end is the one carrying ``value`` where ``where`` says.

    What a CMDB writes next to the serial number it puts on both hosts - "cmdb/kind: board".
    It says which of two hosts is which but not which two hosts belong together, so it is
    read alongside a shared value and never on its own.
    """

    where: SharedLabel | SharedAttribute
    value: str


#: What says which of two hosts sits at the deciding end of a relation, or ``None`` where
#: nothing does and the user is asked per group.
EndMarker = NameWords | MarkedValue | None


@dataclass(frozen=True, kw_only=True)
class RelationToFind:
    """How one relation is looked for.

    Both readings belong to the relation rather than to the scan: a serial number says that
    two hosts are the same machine, and which relation that makes of them is the question the
    finding it stands for has already answered.
    """

    marker: EndMarker = None
    """What marks the host at the deciding end of the relation."""

    shared: SharedValue = None
    """A host label or custom host attribute that pairs the hosts, or ``None`` where the
    names do."""

    @property
    def words(self) -> Sequence[str]:
        """The words its host names carry, where that is what marks the ends."""
        return self.marker.words if isinstance(self.marker, NameWords) else ()

    @property
    def reads_labels(self) -> bool:
        return isinstance(self.shared, SharedLabel) or (
            isinstance(self.marker, MarkedValue) and isinstance(self.marker.where, SharedLabel)
        )


@dataclass(frozen=True, kw_only=True)
class Finding:
    """One thing the user gave a meaning, under the id the page knows it by."""

    id: str
    kind_id: str
    found_by: RelationToFind


@dataclass(frozen=True, kw_only=True)
class Evidence:
    """What a scan reads, as the user confirmed it."""

    findings: Sequence[Finding]
    """In the order the page lists them: where two findings propose the same pair, the pair
    is the first one's."""

    @property
    def reads_labels(self) -> bool:
        return any(finding.found_by.reads_labels for finding in self.findings)


def relation_to_find(
    kind_id: str,
    *,
    words: Sequence[str] = (),
    marked_by: MarkedValue | None = None,
    paired_by: SharedValue = None,
) -> RelationToFind:
    """What one confirmed finding asks the scan for, or a ``ValueError`` saying what is wrong.

    Words pair two hosts and say which is which at the same time. A value that marks one of
    them does only the second, so it needs a value both carry beside it - and a finding with
    neither would read the whole fleet to find nothing.
    """
    if (kind := RELATION_KINDS.get(kind_id)) is None or kind.name_evidence is None:
        raise ValueError(_('No relation "%(kind)s" can be discovered.') % {"kind": kind_id})
    for word in words:
        if not is_name_token(word):
            raise ValueError(
                _('"%(word)s" cannot be read out of a host name: a word is one whole part of it.')
                % {"word": word}
            )
    if words and marked_by is not None:
        raise ValueError(_("A relation is marked either by words or by a value, not by both."))
    if not words and paired_by is None:
        raise ValueError(
            _("Nothing would find this relation: name a word, or a value both hosts carry.")
        )
    return RelationToFind(
        marker=NameWords(tuple(words)) if words else marked_by,
        shared=paired_by,
    )


def pair_key(source: str, kind_id: str, target: str) -> str:
    """What identifies the row of a pair. Named by the kind rather than by the relation, so
    that a row keeps its identity when its direction is answered."""
    return f"{source}|{kind_id}|{target}"


def group_key(kind_id: str, members: Sequence[str]) -> str:
    return f"{kind_id}|{','.join(members)}"


def conflict_key(hosts: tuple[str, str]) -> str:
    return "|".join(hosts)


@dataclass(frozen=True, kw_only=True)
class HostPair:
    """The two hosts of one relation, and which end the first of them sits at.

    ``source`` is the host the relation is stored on - Checkmk mirrors it onto ``target``
    itself - and ``source_direction`` is the end it sits at, so that the pair reads like
    the row it will produce in the host dialog: "this host is the management board of
    <target>".
    """

    source: HostName
    target: HostName
    kind_id: str
    source_direction: RelationDirection

    def __post_init__(self) -> None:
        if not kind_accepts(self.kind_id, self.source_direction):
            raise ValueError(f"No relation {self.kind_id!r} with an end {self.source_direction!r}.")
        if self.source == self.target:
            raise ValueError(f"A host cannot be related to itself: {self.source!r}.")

    @property
    def choice_name(self) -> str:
        """The pair's relation as one name, the way the wire and the dialog spell it."""
        return relation_choice_name(self.kind_id, self.source_direction)

    @property
    def key(self) -> str:
        return pair_key(self.source, self.kind_id, self.target)

    def claim(self) -> tuple[HostName, HostName, str, RelationDirection]:
        """What the pair says, the same whichever of its hosts it is read from."""
        if self.source < self.target:
            return self.source, self.target, self.kind_id, self.source_direction
        return self.target, self.source, self.kind_id, reverse_direction(self.source_direction)


@dataclass(frozen=True)
class NameReason:
    """The name of one host is the other's with this word added."""

    word: str


@dataclass(frozen=True)
class ValueReason:
    """The hosts carry this value in this label or attribute."""

    where: SharedLabel | SharedAttribute
    value: str


#: What a proposal was found by, for a page that shows it without a sentence.
Reason = NameReason | ValueReason


@dataclass(frozen=True, kw_only=True)
class ScannedHost:
    """A host as the discovery reads it - everything the evidence can be taken from.

    Read off a host once: :meth:`Host.labels` walks the folder chain on every call, while
    a scan reads every host against every other.
    """

    name: HostName
    labels: Labels
    attributes: HostAttributes


def at_deciding_end(host: ScannedHost, marker: EndMarker) -> bool:
    """Whether ``marker`` points at this host as the one at the deciding end of its relation.

    Asked of hosts that a shared value has already paired, where the names need not derive
    from one another: "bmc-77" is the board of "blade-77", and a host the CMDB writes
    "cmdb/kind: board" on is one whatever it is called.
    """
    match marker:
        case NameWords(words=words):
            return _marking_word(host.name, words) is not None
        case MarkedValue(where=where, value=value):
            return shared_value(host, where) == value
        case None:
            return False
        case _:
            assert_never(marker)


def _marking_word(name: str, words: Sequence[str]) -> str | None:
    """The first of ``words`` that is a part of ``name``, spelled the way the words are."""
    parts = {part.lower() for part in _PARTS.split(name)}
    return next((word for word in words if word.lower() in parts), None)


def _marked_evidence(host: HostName, marker: EndMarker) -> str:
    """Why ``host`` is the one at the deciding end: what the marker found on it."""
    match marker:
        case NameWords(words=words):
            return _('"%(host)s" has "%(word)s" in its name.') % {
                "host": host,
                "word": _marking_word(host, words),
            }
        case MarkedValue(where=where, value=value):
            template = (
                _('"%(host)s" carries the host label "%(name)s" with the value "%(value)s".')
                if isinstance(where, SharedLabel)
                else _(
                    '"%(host)s" carries the host attribute "%(name)s" with the value "%(value)s".'
                )
            )
            return template % {"host": host, "name": where.name, "value": value}
        case None:
            raise ValueError(marker)
        case _:
            assert_never(marker)


def shared_value(host: ScannedHost, shared: SharedLabel | SharedAttribute) -> str | None:
    """What ``host`` is grouped by on top of its name, or ``None`` if it carries nothing."""
    match shared:
        case SharedLabel(name=name):
            return host.labels.get(name) or None
        case SharedAttribute(name=name):
            value = host.attributes.get(name)
            return value or None if isinstance(value, str) else None
        case _:
            assert_never(shared)


def _name_pairs(hosts: Sequence[ScannedHost]) -> Mapping[str, set[tuple[HostName, HostName]]]:
    """Every word that turns one existing host name into another, with the pairs it does so for.

    The host carrying the word comes first. Read once per scan and looked up per word, so a
    scan asking for ten words reads the fleet once, not ten times.
    """
    known = {str(host.name): host.name for host in hosts}
    found: dict[str, set[tuple[HostName, HostName]]] = {}
    for host in hosts:
        for word, base in _placements(host.name):
            if not is_name_token(word):
                continue
            if (other := known.get(base)) is not None and other != host.name:
                found.setdefault(word.lower(), set()).add((host.name, other))
    return found


#: The most hosts one value may be shared by and still read as one machine - a server, its
#: board, a chassis full of blades. A value shared more widely is a location or an operating
#: system, which says nothing about which two hosts belong together.
_MACHINE_SIZE: Final = 20


@dataclass(frozen=True, kw_only=True)
class Proposal:
    """One relation the configuration speaks for, and what speaks for it."""

    pair: HostPair
    finding: str
    evidence: str
    """Why these two hosts, in the words the row shows; already translated."""
    reason: Reason


@dataclass(frozen=True, kw_only=True)
class GroupProposal:
    """Hosts carrying the same value, with nothing saying which of them sits where.

    Asked as one question rather than offered as each of the pairs it could stand for: the
    user names the host at the deciding end, and the pairs follow from that. That is the
    chassis case as well - one board and every blade that shares its serial number.
    """

    kind_id: str
    finding: str

    direction: RelationDirection
    """The end the host the user names sits at."""

    members: Sequence[HostName]
    evidence: str
    """Why these hosts belong together, in the words the row shows; already translated."""
    reason: ValueReason

    @property
    def key(self) -> str:
        return group_key(self.kind_id, self.members)


@dataclass(frozen=True, kw_only=True)
class Conflict:
    """Two hosts the findings disagree about - one says board, another says the reverse.

    Neither claim is proposed: which of them is right is not in the configuration, and a
    relation stored the wrong way round is worse than one the user answers for.
    """

    hosts: tuple[HostName, HostName]
    claims: Sequence[Proposal]


@dataclass(frozen=True, kw_only=True)
class Proposals:
    """What one scan read off the configuration: what it can say, what it can only ask, and
    where its findings disagree."""

    pairs: Sequence[Proposal] = ()
    groups: Sequence[GroupProposal] = ()
    conflicts: Sequence[Conflict] = ()


def propose_relations(
    hosts: Sequence[ScannedHost],
    *,
    evidence: Evidence,
    kinds: Mapping[str, RelationKind] = RELATION_KINDS,
) -> Proposals:
    """The relations the configuration of ``hosts`` speaks for, and the ones it only hints at.

    Two readings, both of which read the relation off the configuration rather than guess at
    it: a name derived from another host's name, and a value both hosts carry. Where nothing
    says which end is which, the hosts are handed on as a question rather than paired at
    random, and where two findings say different things about the same two hosts, both are
    handed on as a conflict.

    Which relations can be found this way is not this module's business but the kind's: a
    kind is discovered where it declares a :class:`NameEvidence`, and one that does not is
    simply not proposed.
    """
    names = _name_pairs(hosts) if any(not f.found_by.shared for f in evidence.findings) else {}
    claims: list[Proposal] = []
    questions: list[GroupProposal] = []
    for finding in evidence.findings:
        if (kind := kinds.get(finding.kind_id)) is None or kind.name_evidence is None:
            continue
        direction = kind.name_evidence.direction
        if (shared := finding.found_by.shared) is None:
            claims.extend(_from_names(finding, direction, names))
            continue
        pairs, asked = _from_shared_value(hosts, shared, direction, finding)
        claims.extend(pairs)
        questions.extend(asked)
    pairs, conflicts = _settle_claims(claims)
    return Proposals(pairs=pairs, groups=_open_questions(questions, claims), conflicts=conflicts)


def _open_questions(
    questions: Sequence[GroupProposal], claims: Sequence[Proposal]
) -> list[GroupProposal]:
    """Each question once, asking only about the members no claim of its relation places.

    Whatever the user names for a group is stored on top of the claims, so a member a claim
    already places would end up with two boards, or a board with one of its own.
    """
    placed = {
        (claim.pair.kind_id, host)
        for claim in claims
        for host in (claim.pair.source, claim.pair.target)
    }
    open_questions: dict[str, GroupProposal] = {}
    for question in questions:
        members = [host for host in question.members if (question.kind_id, host) not in placed]
        if len(members) >= 2:
            left = replace(question, members=members)
            open_questions.setdefault(left.key, left)
    return list(open_questions.values())


def _from_names(
    finding: Finding,
    direction: RelationDirection,
    names: Mapping[str, set[tuple[HostName, HostName]]],
) -> Iterable[Proposal]:
    """Every host whose name is another host's name plus one of the finding's words, which
    sits at ``direction`` - the end its kind's names mark."""
    for word in finding.found_by.words:
        for named, related in sorted(names.get(word.lower(), ())):
            yield Proposal(
                pair=HostPair(
                    source=named,
                    target=related,
                    kind_id=finding.kind_id,
                    source_direction=direction,
                ),
                finding=finding.id,
                evidence=_('The name is "%(host)s" with "%(token)s" added.')
                % {"host": related, "token": word},
                reason=NameReason(word),
            )


def _settle_claims(claims: Sequence[Proposal]) -> tuple[list[Proposal], list[Conflict]]:
    """The claims that stand, and the pairs of hosts two findings say different things about.

    The same claim made twice - by the name and by a serial number - is one proposal, the
    first finding's. Two different claims about the same two hosts are neither.
    """
    by_hosts: dict[frozenset[HostName], list[Proposal]] = {}
    for claim in claims:
        by_hosts.setdefault(frozenset((claim.pair.source, claim.pair.target)), []).append(claim)

    pairs: list[Proposal] = []
    conflicts: list[Conflict] = []
    for found in by_hosts.values():
        distinct: dict[tuple[HostName, HostName, str, RelationDirection], Proposal] = {}
        for claim in found:
            distinct.setdefault(claim.pair.claim(), claim)
        if len(distinct) == 1:
            pairs.append(found[0])
            continue
        first, second = sorted((found[0].pair.source, found[0].pair.target))
        conflicts.append(Conflict(hosts=(first, second), claims=list(distinct.values())))
    return pairs, conflicts


def _from_shared_value(
    hosts: Sequence[ScannedHost],
    shared: SharedLabel | SharedAttribute,
    direction: RelationDirection,
    finding: Finding,
) -> tuple[Sequence[Proposal], Sequence[GroupProposal]]:
    """What a value several hosts carry says about the finding's relation, whose marked host
    sits at ``direction``, and what it only asks.

    A group holding one host the marker points at is settled: that host sits at the deciding
    end, and it is paired with every other host of the group - the chassis case, one board and
    all of its blades. A group nothing marks is handed on as a question instead of being
    dropped, because the value is evidence enough that the hosts belong together; only which
    of them is which is not in the configuration. A group the marker points at several hosts
    of is neither: the value is shared by more than one machine, and which board belongs to
    which host it does not say.
    """
    marker = finding.found_by.marker

    grouped: dict[str, list[ScannedHost]] = {}
    for host in hosts:
        if (value := shared_value(host, shared)) is not None:
            grouped.setdefault(value, []).append(host)

    pairs: list[Proposal] = []
    questions: list[GroupProposal] = []
    for value, group in grouped.items():
        # A value shared this widely is a category - "board", a location - rather than one
        # machine: pairing by it would relate every host carrying it to every other.
        if not 2 <= len(group) <= _MACHINE_SIZE:
            continue
        match [host for host in group if at_deciding_end(host, marker)]:
            case []:
                # Where both ends read the same, there is nothing to name.
                if direction != "symmetric":
                    questions.append(
                        GroupProposal(
                            kind_id=finding.kind_id,
                            finding=finding.id,
                            direction=direction,
                            members=[host.name for host in group],
                            evidence=_shared_evidence(shared, value, all_of_them=True),
                            reason=ValueReason(shared, value),
                        )
                    )
            case [end]:
                evidence = f"{_shared_evidence(shared, value)} {_marked_evidence(end.name, marker)}"
                pairs.extend(
                    Proposal(
                        pair=HostPair(
                            source=end.name,
                            target=other.name,
                            kind_id=finding.kind_id,
                            source_direction=direction,
                        ),
                        finding=finding.id,
                        evidence=evidence,
                        reason=ValueReason(shared, value),
                    )
                    for other in group
                    if other is not end
                )
            case _:
                pass
    return pairs, questions


def _shared_evidence(
    shared: SharedLabel | SharedAttribute, value: str, *, all_of_them: bool = False
) -> str:
    """Why these hosts belong together, read as a pair or as a whole group."""
    match shared:
        case SharedLabel(name=name):
            template = (
                _('All of them carry the host label "%(name)s" with the value "%(value)s".')
                if all_of_them
                else _('Both carry the host label "%(name)s" with the value "%(value)s".')
            )
        case SharedAttribute(name=name):
            template = (
                _('All of them carry the host attribute "%(name)s" with the value "%(value)s".')
                if all_of_them
                else _('Both carry the host attribute "%(name)s" with the value "%(value)s".')
            )
        case _:
            assert_never(shared)
    return template % {"name": name, "value": value}
