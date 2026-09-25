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
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import assert_never, Final

from cmk.ccc.hostaddress import HostName
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.host_relation_kinds import (
    is_name_token,
    kind_accepts,
    NAME_SEPARATORS,
    RELATION_KINDS,
    RelationKind,
)
from cmk.gui.utils.host_relations import (
    RelationDirection,
    RelationLink,
    reverse_direction,
)
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_config_bundle
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.host_relations import relation_choice_name
from cmk.gui.watolib.hosts_and_folders import (
    FolderTree,
    Host,
    PathWithoutSlash,
    plan_relation_mirror,
    relation_mirror_folders,
)
from cmk.ruleset_matcher.labels import Labels
from cmk.web.utils.escaping import strip_tags

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


class LinkOutcome(StrEnum):
    """What storing one proposed relation does - or why it does nothing.

    :attr:`UNDECIDED` is the one that is not about storing at all: it belongs to a group the
    discovery can only ask about, and turns into one of the others once the user has
    answered it.
    """

    LINK = "link"
    ALREADY_LINKED = "already_linked"
    STORED_OTHERWISE = "stored_otherwise"
    NOT_WRITABLE = "not_writable"
    UNDECIDED = "undecided"


def group_outcome(settled: str | None) -> LinkOutcome:
    """A question is answered once one of its members holds the relation to all the others."""
    return LinkOutcome.ALREADY_LINKED if settled else LinkOutcome.UNDECIDED


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
class RelationEntry:
    """One relation, what speaks for it, and what Setup has to say about storing it."""

    pair: HostPair

    outcome: LinkOutcome

    finding: str = ""
    """The id of the finding that proposed it. Empty for a pair that was named rather than
    found."""

    evidence: str = ""
    """Why the discovery proposes this pair; already translated. Empty for a pair that was
    named rather than found."""

    reason: Reason | None = None
    """What :attr:`evidence` says, taken apart. ``None`` where the evidence is."""

    detail: str = ""
    """Why the outcome is not :attr:`LinkOutcome.LINK`; already translated."""


@dataclass(frozen=True, kw_only=True)
class ScannedHost:
    """A host as the discovery reads it - everything the evidence can be taken from.

    Read off a host once: :meth:`Host.labels` walks the folder chain on every call, while
    a scan reads every host against every other.
    """

    name: HostName
    labels: Labels
    attributes: HostAttributes


def scanned_host(host: Host, *, read_labels: bool) -> ScannedHost:
    """``host`` as the scan reads it.

    The labels are the ones Setup holds for it - its own, its folders' and the ones its
    attributes set - not the ones the monitoring discovered. Read only when a label is what
    the scan pairs or marks on: :meth:`Host.labels` walks the folder chain on every call.
    """
    return ScannedHost(
        name=host.name(),
        labels=host.labels() if read_labels else {},
        attributes=host.attributes,
    )


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


@dataclass(frozen=True, kw_only=True)
class GroupEntry:
    """A question the discovery found, and what Setup has to say about answering it."""

    proposal: GroupProposal

    settled: HostName | None = None
    """The member that already holds this relation to all the others, if there is one."""

    refusals: Mapping[HostName, str] = field(default_factory=dict)
    """Per member that cannot be written, why - such a host cannot be named as the end."""

    @property
    def outcome(self) -> LinkOutcome:
        return group_outcome(self.settled)


@dataclass(frozen=True, kw_only=True)
class ConflictEntry:
    """Two hosts the findings disagree about, each claim with what storing it would do."""

    hosts: tuple[HostName, HostName]
    claims: Sequence[RelationEntry]


@dataclass(frozen=True, kw_only=True)
class Discovery:
    """What a scan found, and how much of Setup it read to find it."""

    hosts_scanned: int
    entries: Sequence[RelationEntry]
    groups: Sequence[GroupEntry] = ()
    conflicts: Sequence[ConflictEntry] = ()


def discover_relations(
    tree: FolderTree,
    *,
    evidence: Evidence,
    acting_user: LoggedInUser,
) -> Discovery:
    """The relations the hosts in ``tree`` speak for, each with what storing it would do.

    Everything is read from Setup rather than from the monitoring, so that a host the core
    does not know yet is found as well.
    """
    all_hosts = readable_hosts(tree, acting_user=acting_user)
    scanned = [scanned_host(host, read_labels=evidence.reads_labels) for host in all_hosts.values()]
    refusal = _refusals_per_folder_pair(acting_user=acting_user)
    found = propose_relations(scanned, evidence=evidence)
    entries = [_settled(proposal, all_hosts, refusal) for proposal in found.pairs]
    conflicts = []
    for conflict in found.conflicts:
        claims = [_settled(claim, all_hosts, refusal) for claim in conflict.claims]
        # One of the claims stored already is the conflict answered - by the user in an earlier
        # run, or by hand. It is not asked again on every scan.
        if stored := [claim for claim in claims if claim.outcome is LinkOutcome.ALREADY_LINKED]:
            entries.extend(stored)
        else:
            conflicts.append(ConflictEntry(hosts=conflict.hosts, claims=claims))
    return Discovery(
        hosts_scanned=len(all_hosts),
        entries=entries,
        groups=[_settled_group(question, all_hosts, refusal) for question in found.groups],
        conflicts=conflicts,
    )


def readable_hosts(tree: FolderTree, *, acting_user: LoggedInUser) -> Mapping[HostName, Host]:
    """Every host of Setup in a folder the user may see.

    The discovery shows host names in examples, rows and questions, so it reads no host the
    folder view would not show either. Asked once per folder rather than once per host.
    """
    readable: dict[PathWithoutSlash, bool] = {}

    def may_read(host: Host) -> bool:
        folder = host.folder()
        if (path := folder.path()) not in readable:
            readable[path] = folder.permissions.may("read", acting_user)
        return readable[path]

    return {
        name: host
        for name, host in tree.root_folder().all_hosts_recursively().items()
        if may_read(host)
    }


def _refusals_per_folder_pair(*, acting_user: LoggedInUser) -> Callable[[Host, Host], str | None]:
    """:func:`_refusal_to_write`, asked once per pair of folders rather than once per pair,
    and then whether the user may edit each of the two hosts, asked once per host.

    Whether a user may write a folder is the same answer for every host in it, and a scan
    of a large fleet asks it tens of thousands of times over a handful of folders. A host can
    still name contact groups of its own that the folder does not.
    """
    seen: dict[tuple[PathWithoutSlash, PathWithoutSlash], str | None] = {}
    editable: dict[HostName, bool] = {}

    def refusal(source: Host, target: Host) -> str | None:
        key = (source.folder().path(), target.folder().path())
        if key not in seen:
            seen[key] = _refusal_to_write(source, target, acting_user=acting_user)
        if seen[key] is not None:
            return seen[key]
        for host in (source, target):
            if (name := host.name()) not in editable:
                editable[name] = host.permissions.may("write", acting_user)
            if not editable[name]:
                return _('No permission to edit the host "%(host)s".') % {"host": name}
        return None

    return refusal


def _settled(
    proposal: Proposal,
    all_hosts: Mapping[HostName, Host],
    refusal: Callable[[Host, Host], str | None],
) -> RelationEntry:
    """What the state of Setup has to say about a pair the discovery found."""
    outcome, detail = _state_of(proposal.pair, all_hosts, refusal)
    return RelationEntry(
        pair=proposal.pair,
        outcome=outcome,
        finding=proposal.finding,
        evidence=proposal.evidence,
        reason=proposal.reason,
        detail=detail,
    )


def _state_of(
    pair: HostPair,
    all_hosts: Mapping[HostName, Host],
    refusal: Callable[[Host, Host], str | None],
) -> tuple[LinkOutcome, str]:
    source, target = all_hosts[pair.source], all_hosts[pair.target]
    if _holds(pair, source, target):
        # No detail: the outcome says this in one word, and a question whose group is settled
        # carries none either - two rows of the same table must not read differently.
        return LinkOutcome.ALREADY_LINKED, ""

    if (otherwise := _stored_otherwise(source, target)) is not None:
        return LinkOutcome.STORED_OTHERWISE, otherwise

    if (locked := _locked_by_quick_setup(source, target)) is not None:
        return LinkOutcome.NOT_WRITABLE, locked

    if (refused := refusal(source, target)) is not None:
        return LinkOutcome.NOT_WRITABLE, refused

    return LinkOutcome.LINK, ""


def _holds(pair: HostPair, source: Host, target: Host) -> bool:
    """Whether the relation ``pair`` asks for is stored already, by either half of it.

    One half is enough: :func:`cmk.gui.watolib.host_relations.resolve_all_relations` derives
    the other, so the monitoring shows the relation whichever of the two hosts stores it.
    """
    link = link_of(pair)
    if source.stores_relations_about(target.name(), [link]):
        return True
    # A source saying something else about the target holds a different relation, not a lost half.
    if not source.stores_relations_about(target.name(), []):
        return False
    other_half = plan_relation_mirror(pair.source, [], [link])[pair.target]
    return target.stores_relations_about(source.name(), other_half)


def _stored_otherwise(source: Host, target: Host) -> str | None:
    """Why this pair must not be written: the two hosts are related in some other way already.

    Storing a pair replaces whatever the two hosts say about each other, so a relation somebody
    entered by hand would be lost without a trace. The discovery proposes, it does not correct.
    """
    for host, other in ((source, target), (target, source)):
        if not host.stores_relations_about(other.name(), []):
            return _('"%(source)s" and "%(target)s" are already related in another way.') % {
                "source": source.name(),
                "target": target.name(),
            }
    return None


def _settled_group(
    proposal: GroupProposal,
    all_hosts: Mapping[HostName, Host],
    refusal: Callable[[Host, Host], str | None],
) -> GroupEntry:
    """What the state of Setup has to say about a question the discovery found."""
    members = [all_hosts[name] for name in proposal.members]
    return GroupEntry(
        proposal=proposal,
        settled=_member_at_end(proposal, members),
        refusals={
            host.name(): reason
            for host in members
            if (reason := _refusal_for_member(host, members, refusal)) is not None
        },
    )


def _refusal_for_member(
    host: Host, members: Sequence[Host], refusal: Callable[[Host, Host], str | None]
) -> str | None:
    """Why this host cannot be the one named: a relation it would take part in cannot be written.

    Asked against the whole group, because naming it is naming every pair it would produce.
    """
    if (locked := _locked_by_quick_setup(host)) is not None:
        return locked
    for other in members:
        if other.name() != host.name() and (refused := refusal(host, other)) is not None:
            return refused
    return None


def _member_at_end(proposal: GroupProposal, members: Sequence[Host]) -> HostName | None:
    """The member that already holds this relation to every other one, if there is one.

    What keeps a second scan from asking again about a group that a run has answered.
    """
    for host in members:
        if all(
            _holds(
                HostPair(
                    source=host.name(),
                    target=other.name(),
                    kind_id=proposal.kind_id,
                    source_direction=proposal.direction,
                ),
                host,
                other,
            )
            for other in members
            if other.name() != host.name()
        ):
            return host.name()
    return None


def _locked_by_quick_setup(*hosts: Host) -> str | None:
    """Why one of these hosts may not be edited at all - asked per host, not per folder.

    ``Host.set_relations_about()`` refuses such a host as well, so this is what keeps the
    proposal honest rather than what keeps the write safe.
    """
    for host in hosts:
        if is_locked_by_config_bundle(host.locked_by()):
            return _("'%(host)s' is locked by Quick setup.") % {"host": host.name()}
    return None


def _refusal_to_write(source: Host, target: Host, *, acting_user: LoggedInUser) -> str | None:
    """Why this pair cannot be written, short enough for a row of the table.

    Worded here rather than taken from the checks: those also list the contact groups, which a
    row repeated for every pair of a folder cannot carry. The checks are asked afterwards all
    the same, so that one added to them later refuses here too.

    Both halves are checked, because both get written. Asked before anything is mutated, in
    the same order ``Host.edit()`` asks it, so that the proposal and the run agree.
    """
    for folder in dict.fromkeys((source.folder(), target.folder())):
        if folder.locked_hosts():
            return _('The hosts in the folder "%(folder)s" are locked.') % {
                "folder": folder.title()
            }
        if not folder.permissions.may("write", acting_user):
            return _('No permission to edit the hosts in the folder "%(folder)s".') % {
                "folder": folder.title()
            }
    try:
        relation_mirror_folders([source, target], acting_user=acting_user)
    except (MKAuthException, MKUserError) as refusal:
        return strip_tags(str(refusal))
    return None


def link_of(pair: HostPair) -> RelationLink:
    """The row the pair will store on its source host."""
    return {"kind": pair.kind_id, "direction": pair.source_direction, "host": pair.target}


def outcome_counts(outcomes: Iterable[LinkOutcome]) -> Mapping[LinkOutcome, int]:
    """How often each outcome occurs, including the outcomes that do not."""
    counted = Counter(outcomes)
    return {outcome: counted.get(outcome, 0) for outcome in LinkOutcome}
