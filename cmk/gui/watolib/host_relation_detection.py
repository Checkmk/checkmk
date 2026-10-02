#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Find the relations the hosts in Setup already show, and store the ones the user confirms.

Relations are stored on both hosts of a pair, which is why every bulk route into the
``relations`` attribute is closed (see
:class:`cmk.gui.watolib.builtin_attributes.HostAttributeRelations`). Onboarding a fleet
still needs one, and this is the shape that keeps the invariant: read the evidence that is
already in the configuration, propose what it speaks for, and let the mirroring primitives
of :mod:`cmk.gui.watolib.hosts_and_folders` do the writing for the proposals the user
accepts.

Detection rather than a rule, the way services are found rather than configured: the two
hosts of a relation say so themselves - a board named after the host it sits in, or a
label the CMDB wrote on both - and a user who has to describe that in regular expressions
is doing the work the configuration has already done.

Finding what to store is separate from storing it, and nothing is stored that was not
named: the run writes the pairs it is handed, not the ones a second scan would find.
"""

import heapq
import re
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import assert_never, Final

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
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
    relations_or_empty,
    reverse_direction,
)
from cmk.gui.watolib.config_domain_name import CORE as CORE_DOMAIN
from cmk.gui.watolib.config_domain_name import generate_hosts_to_update_settings
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_config_bundle
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.host_relations import relation_choice_name
from cmk.gui.watolib.hosts_and_folders import (
    apply_relation_mirror,
    counterpart_resolver,
    diff_attributes,
    Folder,
    FolderTree,
    Host,
    HostEditResult,
    parent_folder_chain,
    PathWithoutSlash,
    plan_relation_mirror,
    relation_mirror_folders,
)
from cmk.gui.watolib.pending_changes import Change, ChangeScope, PendingChanges
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
        raise ValueError(_('No relation "%(kind)s" can be detected.') % {"kind": kind_id})
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


def group_partners[T: str](members: Sequence[T], outside: Collection[str], named: str) -> list[T]:
    """The members of a group the host named in it is related to.

    All the others - but a host named from outside the scope only to the ones inside it, so
    that every relation an answer stores has a host in scope (see :class:`Scope`).
    """
    if named not in outside:
        return [member for member in members if member != named]
    return [member for member in members if member != named and member not in outside]


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
    detection can only ask about, and turns into one of the others once the user has
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
    """Why the detection proposes this pair; already translated. Empty for a pair that was
    named rather than found."""

    reason: Reason | None = None
    """What :attr:`evidence` says, taken apart. ``None`` where the evidence is."""

    detail: str = ""
    """Why the outcome is not :attr:`LinkOutcome.LINK`; already translated."""


@dataclass(frozen=True, kw_only=True)
class ScannedHost:
    """A host as the detection reads it - everything the evidence can be taken from.

    Read off a host once: :meth:`Host.labels` walks the folder chain on every call, while
    a scan reads every host against every other.
    """

    name: HostName
    labels: Labels
    attributes: Mapping[str, object]


def scanned_hosts(hosts: Iterable[Host], *, read_labels: bool) -> list[ScannedHost]:
    """``hosts`` as the scan reads them.

    Attributes and labels are what a host sets itself and what its folders set: a CMDB that
    writes a rack or a chassis onto a folder means it for every host in it, the same as a label
    set there. Not the defaults of the attributes nobody set - a host carries nothing it was
    not given. What a folder sets is read once per folder: a fleet is tens of thousands of
    hosts in a few hundred folders.

    The labels are the ones Setup holds, not the ones the monitoring discovered, and are read
    only when a label is what the scan pairs or marks on.
    """
    set_by_folder: dict[PathWithoutSlash, Mapping[str, object]] = {}

    def _set_by(folder: Folder) -> Mapping[str, object]:
        if (attributes := set_by_folder.get(folder.path())) is None:
            attributes = set_by_folder[folder.path()] = {
                name: value
                for setting in (*parent_folder_chain(folder), folder)
                for name, value in setting.attributes.items()
            }
        return attributes

    return [
        ScannedHost(
            name=host.name(),
            labels=host.labels() if read_labels else {},
            attributes={**_set_by(host.folder()), **host.attributes},
        )
        for host in hosts
    ]


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

    outside: frozenset[HostName] = frozenset()
    """The members out of scope, where the scan has one."""

    @property
    def key(self) -> str:
        return group_key(self.kind_id, self.members)

    def partners(self, named: HostName) -> list[HostName]:
        return group_partners(self.members, self.outside, named)


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
    kind is detected where it declares a :class:`NameEvidence`, and one that does not is
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
    """A question the detection found, and what Setup has to say about answering it."""

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
class Detection:
    """What a scan found, and how many hosts it looked at to find it."""

    hosts_scanned: int
    """The hosts in scope. The others are read too, but only as the other end of a relation."""
    entries: Sequence[RelationEntry]
    groups: Sequence[GroupEntry] = ()
    conflicts: Sequence[ConflictEntry] = ()


@dataclass(frozen=True, kw_only=True)
class Scope:
    """Which relations a scan is after: the ones with a host in this folder or on this site.

    One host of a pair is enough. The boards of a fleet often have a folder of their own
    while the hosts they manage live elsewhere, so every host the user may see is still read
    as the other end.
    """

    folder: PathWithoutSlash = ""
    """Subfolders included; the main folder is all of Setup."""
    site: SiteId | None = None

    def hosts_in(self, tree: FolderTree, hosts: Mapping[HostName, Host]) -> frozenset[HostName]:
        """The names of those of ``hosts`` in scope."""
        names: Collection[HostName]
        if not self.folder:
            names = hosts.keys()
        elif (folder := tree.all_folders().get(self.folder)) is not None:
            names = hosts.keys() & folder.all_hosts_recursively().keys()
        else:
            # Removed since the scan was asked for: nothing is in it any more.
            return frozenset()
        if self.site is None:
            return frozenset(names)
        return frozenset(name for name in names if hosts[name].site_id() == self.site)


#: All of Setup.
EVERYWHERE: Final = Scope()


def _touches(inside: frozenset[HostName], hosts: Iterable[HostName]) -> bool:
    """Whether one of ``hosts`` is in scope."""
    return not inside.isdisjoint(hosts)


def _within(found: Proposals, inside: frozenset[HostName]) -> Proposals:
    """What of ``found`` has a host ``inside``."""
    groups = []
    for group in found.groups:
        if len(outside := frozenset(group.members) - inside) < len(group.members):
            groups.append(replace(group, outside=outside) if outside else group)
    return Proposals(
        pairs=[
            proposal
            for proposal in found.pairs
            if _touches(inside, (proposal.pair.source, proposal.pair.target))
        ],
        groups=groups,
        conflicts=[conflict for conflict in found.conflicts if _touches(inside, conflict.hosts)],
    )


def detect_relations(
    tree: FolderTree,
    *,
    evidence: Evidence,
    acting_user: LoggedInUser,
    scope: Scope = EVERYWHERE,
) -> Detection:
    """The relations the hosts in ``tree`` speak for, each with what storing it would do.

    Everything is read from Setup rather than from the monitoring, so that a host the core
    does not know yet is found as well.
    """
    all_hosts = readable_hosts(tree, acting_user=acting_user)
    scanned = scanned_hosts(all_hosts.values(), read_labels=evidence.reads_labels)
    refusal = _refusals_per_folder_pair(acting_user=acting_user)
    inside = scope.hosts_in(tree, all_hosts)
    found = _within(propose_relations(scanned, evidence=evidence), inside)
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
    return Detection(
        hosts_scanned=len(inside),
        entries=entries,
        groups=[_settled_group(question, all_hosts, refusal) for question in found.groups],
        conflicts=conflicts,
    )


def readable_hosts(tree: FolderTree, *, acting_user: LoggedInUser) -> Mapping[HostName, Host]:
    """Every host of Setup in a folder the user may see.

    The detection shows host names in examples, rows and questions, so it reads no host the
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


#: How many words a suggestion offers that no kind declares: enough to show a fleet's own
#: habit, few enough that the page does not turn into a list of every part of every name.
_WORD_LIMIT: Final = 8

#: How many real pairs a finding shows to say what it means.
_EXAMPLE_LIMIT: Final = 2

#: How many hosts sharing a value an example names: a chassis has dozens, a category hundreds.
_EXAMPLE_HOSTS: Final = 4

#: How many values a label must share out a handful of hosts at a time to read as an identity.
#: Two such values are as likely a category - board and server, two locations - as a serial.
_MACHINE_MIN: Final = 3

#: How many labels and attributes a suggestion offers as values hosts share.
_VALUE_LIMIT: Final = 5

#: The most distinct values a label may have fleet-wide to tell the hosts of a machine apart:
#: "board" and "server" do, a serial number does not. Also what keeps the search cheap - only
#: these few labels are read per group.
_CATEGORY_SIZE: Final = 10


@dataclass(frozen=True, kw_only=True)
class WordFinding:
    """Hosts named like another host with this word added."""

    word: str
    pairs: int
    examples: Sequence[tuple[HostName, HostName]]
    """A few of the pairs, the host carrying the word first."""
    kind_id: str | None
    """The relation whose vendors use this word, or ``None`` for one no kind declares - what
    that one stands for, only the user can say."""


@dataclass(frozen=True, kw_only=True)
class NamesTellApart:
    """In each group one host carries one of these words in its name, and that one is at the
    end the word stands for."""

    kind_id: str | None
    """The relation whose vendors use the words, or ``None`` for words only the user gave."""

    words: Sequence[str]
    """The words that told the hosts apart, the most frequent first."""

    groups: int
    """In how many groups exactly one host carries one of them."""


@dataclass(frozen=True, kw_only=True)
class ValueTellsApart:
    """In each group one host carries a value of ``where`` no other host of the group does.

    Which end that value stands for is not in the data - "board" and "server" both stand
    alone in their group - so the user picks it, and :attr:`suggested` is the one Checkmk can
    tell, if any.
    """

    where: SharedLabel | SharedAttribute

    values: Sequence[tuple[str, int]]
    """Each value, with the number of groups in which exactly one host carries it."""

    suggested: str | None
    """The value that reads like the deciding end - it has a word a kind declares in it."""


#: What tells the hosts sharing a value apart, or ``None`` where nothing does.
TellApart = NamesTellApart | ValueTellsApart | None


@dataclass(frozen=True, kw_only=True)
class ValueExample:
    """One value of a finding, with a few of the hosts sharing it."""

    value: str
    hosts: Sequence[HostName]
    """The first of them by name."""
    size: int
    """How many hosts share it."""


@dataclass(frozen=True, kw_only=True)
class ValueFinding:
    """A label or attribute whose values each sit on a handful of hosts: a serial number."""

    where: SharedLabel | SharedAttribute
    groups: int
    """How many values are each shared by a handful of hosts - the ones that can pair them."""
    largest_group: int
    examples: Sequence[ValueExample]
    """A few of the values."""
    too_wide: int = 0
    """How many values are shared by more hosts than one machine has. These pair nothing, and
    a finding that has only such values is a category rather than an identity."""
    told_apart: TellApart = None
    """What says which host of each group is which, as far as the hosts give it away."""


@dataclass(frozen=True, kw_only=True)
class Suggestions:
    """What the hosts give away about belonging together, before anybody asked for anything."""

    hosts_scanned: int
    """The hosts in scope, as for :class:`Detection`."""
    words: Sequence[WordFinding]
    values: Sequence[ValueFinding]
    label_names: Sequence[str]
    """Every host label there is, for a finding whose board carries a label value."""
    attribute_names: Sequence[str]


def suggest_evidence(
    hosts: Sequence[ScannedHost],
    *,
    attribute_names: Sequence[str],
    words: Sequence[str] = (),
    values: Sequence[SharedLabel | SharedAttribute] = (),
    in_names: bool = True,
    in_values: bool = True,
    inside: frozenset[HostName],
    kinds: Mapping[str, RelationKind] = RELATION_KINDS,
) -> Suggestions:
    """What the detection could look for in ``hosts``, found in the hosts themselves.

    ``words`` and ``values`` are the ones the user added, reported whatever they find - even
    nothing - so the page can show what each of them would read before it is used.
    ``in_names`` and ``in_values`` say where to look at all: a fleet named by convention has
    no use for a list of every label that happens to pair two hosts. Only pairs and groups
    with a host ``inside`` count (see :class:`Scope`).
    """
    declared = _declared_words(kinds)
    return Suggestions(
        hosts_scanned=len(inside),
        words=(
            _word_findings(hosts, requested=words, declared=declared, inside=inside)
            if in_names
            else []
        ),
        values=(
            _value_findings(
                hosts,
                attribute_names,
                requested=values,
                words=words,
                declared=declared,
                inside=inside,
            )
            if in_values
            else []
        ),
        label_names=sorted({name for host in hosts for name in host.labels}) if in_values else [],
        attribute_names=sorted(attribute_names) if in_values else [],
    )


def scan_for_evidence(
    tree: FolderTree,
    *,
    attribute_names: Sequence[str],
    acting_user: LoggedInUser,
    words: Sequence[str] = (),
    values: Sequence[SharedLabel | SharedAttribute] = (),
    in_names: bool = True,
    in_values: bool = True,
    scope: Scope = EVERYWHERE,
) -> Suggestions:
    """:func:`suggest_evidence` for every host the user may see, read the way a scan reads them."""
    hosts = readable_hosts(tree, acting_user=acting_user)
    return suggest_evidence(
        scanned_hosts(hosts.values(), read_labels=in_values),
        attribute_names=attribute_names,
        words=words,
        values=values,
        in_names=in_names,
        in_values=in_values,
        inside=scope.hosts_in(tree, hosts),
    )


def _declared_words(kinds: Mapping[str, RelationKind]) -> Mapping[str, str]:
    """Every word a kind declares, lowered, with the kind that declares it."""
    return {
        token.lower(): kind.id
        for kind in kinds.values()
        if (evidence := kind.name_evidence) is not None
        for token in evidence.tokens
    }


def _word_findings(
    hosts: Sequence[ScannedHost],
    *,
    requested: Sequence[str],
    declared: Mapping[str, str],
    inside: frozenset[HostName],
) -> Sequence[WordFinding]:
    """Every word that turns one existing host name into another, the declared ones first."""
    wanted = {word.lower() for word in requested}
    # A number is not offered as a word: "srv-01" is not "srv" with "01" added. One the user
    # typed is counted all the same - the scan would read it, so the count has to say so.
    in_scope = {
        word: {pair for pair in pairs if _touches(inside, pair)}
        for word, pairs in _name_pairs(hosts).items()
        if not word.isdigit() or word in wanted
    }
    found = {word: pairs for word, pairs in in_scope.items() if pairs}
    findings = []
    for word in {*found, *wanted}:
        pairs = found.get(word, set())
        findings.append(
            WordFinding(
                word=word,
                pairs=len(pairs),
                examples=heapq.nsmallest(_EXAMPLE_LIMIT, pairs),
                kind_id=declared.get(word),
            )
        )
    findings.sort(key=lambda finding: (finding.kind_id is None, -finding.pairs, finding.word))
    undeclared = [finding for finding in findings if finding.kind_id is None]
    offered = {finding.word for finding in undeclared[:_WORD_LIMIT]} | wanted
    return [
        finding for finding in findings if finding.kind_id is not None or finding.word in offered
    ]


def _value_findings(
    hosts: Sequence[ScannedHost],
    attribute_names: Sequence[str],
    *,
    requested: Sequence[SharedLabel | SharedAttribute],
    words: Sequence[str],
    declared: Mapping[str, str],
    inside: frozenset[HostName],
) -> Sequence[ValueFinding]:
    """The labels and attributes whose shared values each look like one machine.

    Checkmk's own labels are left out: none of them is a serial number, and "cmk/site" alone
    would otherwise be offered on every fleet. What the user asked for is reported whatever it
    looks like, counting every value two hosts or more share - how widely is what the user has
    to see before relying on it.
    """
    wanted = set(requested)
    wanted_labels = {where.name for where in requested if isinstance(where, SharedLabel)}
    attributes = [SharedAttribute(name) for name in attribute_names]
    attributes.extend(
        where
        for where in requested
        if isinstance(where, SharedAttribute) and where not in attributes
    )
    # One instance per label name rather than one per host and label: the fleet is read once,
    # and every lookup below hashes it.
    labels: dict[str, SharedLabel] = {}
    grouped: dict[SharedLabel | SharedAttribute, dict[str, list[HostName]]] = {}
    for host in hosts:
        for name in host.labels:
            if name.startswith("cmk/") and name not in wanted_labels:
                continue
            label = labels.get(name) or labels.setdefault(name, SharedLabel(name))
            if (value := shared_value(host, label)) is not None:
                grouped.setdefault(label, {}).setdefault(value, []).append(host.name)
        for attribute in attributes:
            if (value := shared_value(host, attribute)) is not None:
                grouped.setdefault(attribute, {}).setdefault(value, []).append(host.name)

    def split(
        by_value: Mapping[str, list[HostName]],
    ) -> tuple[list[tuple[str, list[HostName]]], list[tuple[str, list[HostName]]]]:
        # Out of scope is only what pairs; the categories below still count every value. The
        # size goes first: most values of a label sit on one host and pair nothing anyway.
        machines = [
            (v, members)
            for v, members in by_value.items()
            if 2 <= len(members) <= _MACHINE_SIZE and _touches(inside, members)
        ]
        wider = [
            (v, members)
            for v, members in by_value.items()
            if len(members) > _MACHINE_SIZE and _touches(inside, members)
        ]
        return machines, wider

    candidates = []
    for where, by_value in grouped.items():
        if where in wanted:
            continue
        machines, wider = split(by_value)
        if len(machines) >= _MACHINE_MIN and len(machines) > len(wider):
            candidates.append((where, machines, wider))
    candidates.sort(key=lambda candidate: (-len(candidate[1]), candidate[0].name))
    offered = [
        *candidates[:_VALUE_LIMIT],
        *((where, *split(grouped.get(where, {}))) for where in requested),
    ]

    telling = _TellingApart(
        hosts=hosts,
        categories=[
            where for where, by_value in grouped.items() if 2 <= len(by_value) <= _CATEGORY_SIZE
        ],
        words=words,
        declared=declared,
    )
    return [
        ValueFinding(
            where=where,
            groups=len(machines),
            largest_group=max((len(members) for _value, members in [*machines, *wider]), default=0),
            # What a value that pairs nothing looks like is what the user has to see to believe it.
            examples=_first_groups(machines or wider, inside),
            too_wide=len(wider),
            told_apart=telling.told_apart(where, machines) if machines else None,
        )
        for where, machines, wider in offered
    ]


def _first_groups(
    groups: Sequence[tuple[str, Sequence[HostName]]], inside: frozenset[HostName]
) -> list[ValueExample]:
    """The groups whose members sort first, without sorting all of them.

    An example names the hosts in scope first: they are what made the group count.
    """
    first = heapq.nsmallest(_EXAMPLE_LIMIT, groups, key=lambda group: min(group[1]))
    examples = [
        ValueExample(
            value=value,
            hosts=heapq.nsmallest(
                _EXAMPLE_HOSTS,
                members,
                key=lambda name: (name not in inside, name),
            ),
            size=len(members),
        )
        for value, members in first
    ]
    return sorted(examples, key=lambda example: example.hosts[0])


#: What splits a value into the words it is made of: "mgmt-board" reads as "mgmt" and "board".
_VALUE_PARTS: Final = re.compile(r"[^a-z0-9]+")


class _TellingApart:
    """What tells the hosts of each group apart, read once per suggestion.

    Whatever marks one host per group and no other: a word a kind declares in its name, or a
    value of a label with few values fleet-wide - "cmdb/kind: board". Names win a tie, because
    they also say which end the host sits at.
    """

    def __init__(
        self,
        *,
        hosts: Sequence[ScannedHost],
        categories: Sequence[SharedLabel | SharedAttribute],
        words: Sequence[str],
        declared: Mapping[str, str],
    ) -> None:
        self._by_name = {host.name: host for host in hosts}
        self._categories = categories
        self._declared = declared
        self._marking_words = [*self._declared, *(w.lower() for w in words)]

    def told_apart(
        self,
        where: SharedLabel | SharedAttribute,
        machines: Sequence[tuple[str, Sequence[HostName]]],
    ) -> TellApart:
        groups = [[self._by_name[member] for member in members] for _value, members in machines]

        named: Counter[str] = Counter()
        named_groups = 0
        for group in groups:
            marked = [
                word
                for host in group
                if (word := _marking_word(host.name, self._marking_words)) is not None
            ]
            if len(marked) == 1:
                named_groups += 1
                named[marked[0]] += 1
        by_names = (
            NamesTellApart(
                kind_id=self._declared.get(named.most_common(1)[0][0]),
                words=[word for word, _count in named.most_common()],
                groups=named_groups,
            )
            if named_groups
            else None
        )
        # Names that settle every group cannot be beaten, and a fleet named this way is the
        # common case: the labels need not be read at all.
        if by_names is not None and named_groups == len(groups):
            return by_names

        standing_alone: Counter[tuple[SharedLabel | SharedAttribute, str]] = Counter()
        for group in groups:
            for category in self._categories:
                if category == where:
                    continue
                carried = Counter(
                    value for host in group if (value := shared_value(host, category)) is not None
                )
                standing_alone.update(
                    (category, value) for value, count in carried.items() if count == 1
                )

        by_category: dict[SharedLabel | SharedAttribute, list[tuple[str, int]]] = {}
        for (category, value), told in standing_alone.items():
            if told >= 2:
                by_category.setdefault(category, []).append((value, told))
        best = max(
            by_category.items(),
            key=lambda item: (max(told for _value, told in item[1]), -len(item[1])),
            default=None,
        )
        if best is None or (by_names is not None and named_groups >= max(t for _v, t in best[1])):
            return by_names
        category, values = best
        values.sort(key=lambda item: (-item[1], item[0]))
        return ValueTellsApart(where=category, values=values, suggested=self._suggested(values))

    def _suggested(self, values: Sequence[tuple[str, int]]) -> str | None:
        reading = [
            value
            for value, _groups in values
            if set(_VALUE_PARTS.split(value.lower())) & self._declared.keys()
        ]
        return reading[0] if len(reading) == 1 else None


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
    """What the state of Setup has to say about a pair the detection found."""
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
    entered by hand would be lost without a trace. The detection proposes, it does not correct.
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
    """What the state of Setup has to say about a question the detection found."""
    members = [all_hosts[name] for name in proposal.members]
    return GroupEntry(
        proposal=proposal,
        settled=_member_at_end(proposal, all_hosts),
        refusals={
            host.name(): reason
            for host in members
            if (reason := _refusal_for_member(proposal, host, all_hosts, refusal)) is not None
        },
    )


def _refusal_for_member(
    proposal: GroupProposal,
    host: Host,
    all_hosts: Mapping[HostName, Host],
    refusal: Callable[[Host, Host], str | None],
) -> str | None:
    """Why this host cannot be the one named: a relation it would take part in cannot be written.

    Asked against all its partners, because naming it is naming every pair it would produce.
    """
    if (locked := _locked_by_quick_setup(host)) is not None:
        return locked
    for other in proposal.partners(host.name()):
        if (refused := refusal(host, all_hosts[other])) is not None:
            return refused
    return None


def _member_at_end(proposal: GroupProposal, all_hosts: Mapping[HostName, Host]) -> HostName | None:
    """The member that already holds this relation to all its partners, if there is one.

    What keeps a second scan from asking again about a group that a run has answered.
    """
    for name in proposal.members:
        host = all_hosts[name]
        if all(
            _holds(
                HostPair(
                    source=name,
                    target=other,
                    kind_id=proposal.kind_id,
                    source_direction=proposal.direction,
                ),
                host,
                all_hosts[other],
            )
            for other in proposal.partners(name)
        ):
            return name
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


def relation_row_titles() -> Mapping[str, str]:
    """How each relation reads in a proposed row - the page has no vocabulary of its own."""
    return {
        relation_choice_name(kind.id, direction): str(kind.end(direction).row)
        for kind in RELATION_KINDS.values()
        for direction in kind.directions()
    }


def relation_end_nouns() -> Mapping[str, str]:
    """What the host at each end is called - what a row asking for one has to name."""
    return {
        relation_choice_name(kind.id, direction): str(kind.end(direction).noun)
        for kind in RELATION_KINDS.values()
        for direction in kind.directions()
    }


def detectable_kinds() -> Mapping[str, str]:
    """The relations a finding can stand for, each by the relation the host it marks holds."""
    return {
        kind.id: relation_choice_name(kind.id, evidence.direction)
        for kind in RELATION_KINDS.values()
        if (evidence := kind.name_evidence) is not None
    }


def detectable_kind_words() -> Mapping[str, list[str]]:
    """Per kind a finding can stand for, the words its vendors habitually put in host names."""
    return {
        kind.id: list(evidence.tokens)
        for kind in RELATION_KINDS.values()
        if (evidence := kind.name_evidence) is not None
    }


@dataclass
class _Touched:
    """A host a run changed, with what it was before the run."""

    host: Host
    before: HostAttributes
    counterparts: set[HostName] = field(default_factory=set)
    sites: set[SiteId] = field(default_factory=set)


@dataclass
class _Batch:
    """What a run has touched so far.

    Collected rather than written per pair: ``Host.edit()`` saves the folder on every call,
    which would rewrite the same "hosts.mk" once per host of it, and it records a change per
    half - a board of sixteen blades would be logged sixteen times. Each host is written once
    and logged once, with what the whole run changed about it.
    """

    folders: dict[PathWithoutSlash, Folder] = field(default_factory=dict)
    hosts: dict[HostName, _Touched] = field(default_factory=dict)

    def record(
        self,
        edited: Sequence[tuple[Host, HostEditResult]],
        unchanged: Mapping[HostName, HostAttributes],
        *,
        acting_user: LoggedInUser,
    ) -> None:
        # The folders of the hosts that were changed, not of the pair as the run looked it up:
        # a counterpart may sit on another instance of the same folder (see
        # counterpart_resolver()), and saving that one would silently drop the write.
        self.folders.update(
            relation_mirror_folders([host for host, _edit in edited], acting_user=acting_user)
        )
        for host, edit in edited:
            if (touched := self.hosts.get(host.name())) is None:
                touched = self.hosts[host.name()] = _Touched(
                    host=host, before=unchanged[host.name()]
                )
            touched.counterparts.update(edit.counterpart_hosts)
            touched.sites.update(edit.affected_sites)

    def log(self, pending_changes: PendingChanges) -> None:
        for name, touched in self.hosts.items():
            nodes = touched.host.cluster_nodes()
            pending_changes.add(
                Change(
                    action_name="detect-relations",
                    text=_("Stored detected relations of host %(host)s.") % {"host": name},
                    object_ref=touched.host.object_ref(),
                    diff_text=diff_attributes(
                        touched.before, nodes, touched.host.attributes, nodes
                    ),
                    domains=[CORE_DOMAIN],
                    domain_settings={
                        CORE_DOMAIN: generate_hosts_to_update_settings(
                            sorted({name, *touched.counterparts})
                        )
                    },
                ),
                ChangeScope.sites(sorted(touched.sites)),
            )


def link_relations(
    accepted: Sequence[HostPair],
    tree: FolderTree,
    *,
    pprint_value: bool,
    pending_changes: PendingChanges,
    acting_user: LoggedInUser,
    progress: Callable[[RelationEntry], None],
) -> Sequence[RelationEntry]:
    """Store every relation in ``accepted``, and report what came of each, in the same order.

    A pair that cannot be written is reported and the run goes on: one locked folder in a
    fleet of four hundred must not cost the other three hundred and ninety nine.
    """
    batch = _Batch()
    done: list[RelationEntry] = []
    for pair in accepted:
        settled = _link_pair(pair, tree, batch, acting_user=acting_user)
        done.append(settled)
        progress(settled)

    for folder in batch.folders.values():
        folder.save_hosts(pprint_value=pprint_value, acting_user=acting_user)

    batch.log(pending_changes)
    return done


def _link_pair(
    pair: HostPair, tree: FolderTree, batch: _Batch, *, acting_user: LoggedInUser
) -> RelationEntry:
    """Store the one relation ``pair`` asks for, mutating in memory only."""
    source, target = tree.host(pair.source), tree.host(pair.target)
    if source is None or target is None:
        # Deleted between the scan and the run. Not an error of the detection, but not
        # something to pass over silently either.
        return RelationEntry(
            pair=pair, outcome=LinkOutcome.NOT_WRITABLE, detail=_("The host is gone.")
        )

    try:
        return _write_pair(pair, source, target, batch, acting_user=acting_user)
    except (MKAuthException, MKUserError) as refusal:
        return RelationEntry(pair=pair, outcome=LinkOutcome.NOT_WRITABLE, detail=str(refusal))


def _write_pair(
    pair: HostPair, source: Host, target: Host, batch: _Batch, *, acting_user: LoggedInUser
) -> RelationEntry:
    """The order ``Host.edit()`` establishes: refuse before the first write, then both halves."""
    link = link_of(pair)
    if _holds(pair, source, target):
        return RelationEntry(pair=pair, outcome=LinkOutcome.ALREADY_LINKED)
    # Asked again rather than trusted from the scan: somebody may have related the two hosts
    # by hand since, and that relation is not the detection's to replace.
    if (otherwise := _stored_otherwise(source, target)) is not None:
        return RelationEntry(pair=pair, outcome=LinkOutcome.STORED_OTHERWISE, detail=otherwise)

    unchanged = {host.name(): host.attributes for host in (source, target)}
    before = relations_or_empty(source.attributes.get("relations", []))
    relation_mirror_folders([source, target], acting_user=acting_user)

    if (edit := source.set_relations_about(target.name(), [link], acting_user=acting_user)) is None:
        return RelationEntry(pair=pair, outcome=LinkOutcome.ALREADY_LINKED)

    try:
        mirrored = apply_relation_mirror(
            counterpart_resolver(source.folder()),
            source.name(),
            plan_relation_mirror(
                source.name(),
                before,
                relations_or_empty(source.attributes.get("relations", [])),
            ),
            site_id=source.site_id(),
            acting_user=acting_user,
        )
    except MKAuthException, MKUserError:
        # Unlike in Host.edit(), the source does not die with the request: its folder is saved
        # at the end of the run if any other pair touched it.
        source.attributes = unchanged[source.name()]
        raise
    batch.record([(source, edit), *mirrored], unchanged, acting_user=acting_user)
    return RelationEntry(pair=pair, outcome=LinkOutcome.LINK)


def outcome_label(outcome: LinkOutcome) -> str:
    """What an outcome is called where it is reported as running text."""
    match outcome:
        case LinkOutcome.LINK:
            return _("stored")
        case LinkOutcome.ALREADY_LINKED:
            return _("already related")
        case LinkOutcome.STORED_OTHERWISE:
            return _("related in another way")
        case LinkOutcome.NOT_WRITABLE:
            return _("could not be stored")
        case LinkOutcome.UNDECIDED:
            return _("not answered")
        case _:
            assert_never(outcome)


def run_summary(entries: Sequence[RelationEntry]) -> str:
    """The run in one line, naming only the outcomes it actually had."""
    return ", ".join(
        "%(count)d %(label)s" % {"count": count, "label": outcome_label(outcome)}
        for outcome, count in outcome_counts(entry.outcome for entry in entries).items()
        if count
    )
