#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The relation discovery as background jobs: a scan that is kept, and a run that stores from it.

A fleet of fifty thousand hosts proposes tens of thousands of relations - too many to send to a
browser on every scan, and far too many to send back when they are accepted. So a scan is kept
where it was made, in the work directory of its job, the way the service discovery keeps its
preview (see :class:`cmk.gui.watolib.services.ServiceDiscoveryBackgroundJob`): the page reads it
a page at a time, and accepting names the scan and what the user changed about it rather than
every pair. What is stored is still exactly what was shown.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never, Final, Literal, override

from pydantic import BaseModel

from cmk.ccc import store
from cmk.ccc.hostaddress import HostName
from cmk.ccc.resulttype import Result
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.background_job.job import (
    AlreadyRunningError,
    BackgroundJob,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.i18n import _
from cmk.gui.job_scheduler_client import StartupError
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import AnnotatedUserId, CustomHostAttrSpec
from cmk.gui.utils.host_relations import RelationDirection
from cmk.gui.utils.misc import gen_id
from cmk.gui.utils.roles import UserPermissions, UserPermissionSerializableConfig
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.host_relation_discovery import (
    conflict_key,
    ConflictEntry,
    discover_relations,
    Discovery,
    Evidence,
    Finding,
    group_key,
    group_outcome,
    group_partners,
    GroupEntry,
    HostPair,
    link_relations,
    LinkOutcome,
    MarkedValue,
    NameReason,
    outcome_counts,
    outcome_label,
    pair_key,
    Reason,
    relation_to_find,
    RelationEntry,
    run_summary,
    Scope,
    SharedAttribute,
    SharedLabel,
    ValueReason,
)
from cmk.gui.watolib.hosts_and_folders import FolderTree, HostsAndFoldersConfig
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.livestatus_client import SiteConfigurations
from cmk.ruleset_matcher.tags import TagConfig, TagConfigSpec
from cmk.utils.paths import configuration_lockfile

ValueSource = Literal["label", "attribute"]


class ValueArgs(BaseModel, frozen=True):
    """A host label or custom host attribute, by name."""

    source: ValueSource
    name: str

    def where(self) -> SharedLabel | SharedAttribute:
        return SharedLabel(self.name) if self.source == "label" else SharedAttribute(self.name)


def value_source(where: SharedLabel | SharedAttribute) -> ValueSource:
    """How the wire names where a value is read from - the reverse of :meth:`ValueArgs.where`."""
    match where:
        case SharedLabel():
            return "label"
        case SharedAttribute():
            return "attribute"
        case _:
            assert_never(where)


class MarkArgs(ValueArgs, frozen=True):
    value: str


class FindingArgs(BaseModel, frozen=True):
    """One finding the user gave a meaning, as it travels to the scan job."""

    id: str
    kind_id: str
    words: list[str] = []
    marked_by: MarkArgs | None = None
    paired_by: ValueArgs | None = None


class ScopeArgs(BaseModel, frozen=True):
    """Where the scan looks, as it travels to the scan job (see :class:`Scope`)."""

    folder: str = ""
    site: SiteId | None = None

    def scope(self) -> Scope:
        return Scope(folder=self.folder, site=self.site)


def evidence_of(findings: Sequence[FindingArgs]) -> Evidence:
    """What the findings ask the scan for, or a ``ValueError`` naming the one at fault."""
    return Evidence(
        findings=[
            Finding(
                id=finding.id,
                kind_id=finding.kind_id,
                found_by=relation_to_find(
                    finding.kind_id,
                    words=finding.words,
                    marked_by=(
                        None
                        if finding.marked_by is None
                        else MarkedValue(
                            where=finding.marked_by.where(), value=finding.marked_by.value
                        )
                    ),
                    paired_by=None if finding.paired_by is None else finding.paired_by.where(),
                ),
            )
            for finding in findings
        ]
    )


class FoundReason(BaseModel, frozen=True):
    """What a row was found by: a word in a host name, or a value both hosts carry."""

    word: str | None = None
    source: ValueSource | None = None
    name: str | None = None
    value: str | None = None


def _found_reason(reason: Reason | None) -> FoundReason | None:
    match reason:
        case None:
            return None
        case NameReason(word=word):
            return FoundReason(word=word)
        case ValueReason(where=where, value=value):
            return FoundReason(
                source=value_source(where),
                name=where.name,
                value=value,
            )
        case _:
            assert_never(reason)


class FoundRelation(BaseModel, frozen=True):
    """One relation as the page shows it, with what storing it does."""

    finding: str
    # Host names as plain strings: a scan is read back on every page of it, and validating
    # fifty thousand names each time costs more than the page. They were valid when found.
    source: str
    target: str
    kind_id: str
    source_direction: RelationDirection
    folders: tuple[str, str]
    """The folders of the source and the target host, for the page to filter by."""
    outcome: LinkOutcome
    evidence: str = ""
    reason: FoundReason | None = None
    detail: str = ""

    @property
    def key(self) -> str:
        return pair_key(self.source, self.kind_id, self.target)

    def pair(self) -> HostPair:
        return HostPair(
            source=HostName(self.source),
            target=HostName(self.target),
            kind_id=self.kind_id,
            source_direction=self.source_direction,
        )


class FoundGroup(BaseModel, frozen=True):
    """Hosts sharing a value with nothing saying which of them is which."""

    finding: str
    kind_id: str
    direction: RelationDirection
    members: list[str]
    folders: list[str]
    evidence: str
    reason: FoundReason
    settled: str | None
    refusals: dict[str, str]
    outside: list[str]
    """The members out of scope, where the scan has one."""

    @property
    def key(self) -> str:
        return group_key(self.kind_id, self.members)

    @property
    def outcome(self) -> LinkOutcome:
        return group_outcome(self.settled)

    def partners(self, named: str) -> list[str]:
        """The hosts ``named`` is related to when it is named - none that cannot be written."""
        return [
            partner
            for partner in group_partners(self.members, self.outside, named)
            if partner not in self.refusals
        ]


class FoundConflict(BaseModel, frozen=True):
    """Two hosts the findings disagree about, and what each of them claims."""

    hosts: tuple[str, str]
    claims: list[FoundRelation]

    @property
    def key(self) -> str:
        return conflict_key(self.hosts)


class ScanResult(BaseModel):
    """A scan, as it is kept for the page to read and for a run to store from."""

    hosts_scanned: int
    findings: list[str]
    """The ids of the findings the scan read, in the order the page lists them."""
    relations: list[FoundRelation]
    groups: list[FoundGroup]
    conflicts: list[FoundConflict]


#: The order rows are listed in: what can be stored first, what is done already last.
_OUTCOME_ORDER: Final = {
    LinkOutcome.UNDECIDED: 0,
    LinkOutcome.LINK: 1,
    LinkOutcome.STORED_OTHERWISE: 2,
    LinkOutcome.NOT_WRITABLE: 3,
    LinkOutcome.ALREADY_LINKED: 4,
}


def scan_result(
    discovery: Discovery, *, findings: Sequence[str], folder_of: Callable[[HostName], str]
) -> ScanResult:
    """``discovery`` in the shape it is kept in."""
    return ScanResult(
        hosts_scanned=discovery.hosts_scanned,
        findings=list(findings),
        relations=sorted(
            (_found_relation(entry, folder_of) for entry in discovery.entries),
            key=lambda row: (_OUTCOME_ORDER[row.outcome], row.source, row.target),
        ),
        groups=sorted(
            (_found_group(group, folder_of) for group in discovery.groups),
            key=lambda group: (_OUTCOME_ORDER[group.outcome], group.members),
        ),
        conflicts=[_found_conflict(conflict, folder_of) for conflict in discovery.conflicts],
    )


def _found_relation(entry: RelationEntry, folder_of: Callable[[HostName], str]) -> FoundRelation:
    return FoundRelation(
        finding=entry.finding,
        source=entry.pair.source,
        target=entry.pair.target,
        kind_id=entry.pair.kind_id,
        source_direction=entry.pair.source_direction,
        folders=(folder_of(entry.pair.source), folder_of(entry.pair.target)),
        outcome=entry.outcome,
        evidence=entry.evidence,
        reason=_found_reason(entry.reason),
        detail=entry.detail,
    )


def _found_group(group: GroupEntry, folder_of: Callable[[HostName], str]) -> FoundGroup:
    reason = _found_reason(group.proposal.reason)
    assert reason is not None
    return FoundGroup(
        finding=group.proposal.finding,
        kind_id=group.proposal.kind_id,
        direction=group.proposal.direction,
        members=list(group.proposal.members),
        folders=sorted({folder_of(member) for member in group.proposal.members}),
        evidence=group.proposal.evidence,
        reason=reason,
        settled=group.settled,
        refusals={str(host): refusal for host, refusal in group.refusals.items()},
        outside=sorted(group.proposal.outside),
    )


def _found_conflict(conflict: ConflictEntry, folder_of: Callable[[HostName], str]) -> FoundConflict:
    return FoundConflict(
        hosts=(conflict.hosts[0], conflict.hosts[1]),
        claims=[_found_relation(claim, folder_of) for claim in conflict.claims],
    )


#: How many relations a finding shows to say what storing it would do.
SAMPLE_SIZE: Final = 5


@dataclass(frozen=True, kw_only=True)
class FindingSummary:
    """What one finding of a scan comes to."""

    id: str
    counts: Mapping[LinkOutcome, int]
    """Its relations by outcome. Groups are counted apart: a group is not a relation."""
    samples: Sequence[FoundRelation]
    """A few of its relations, spread over all of them rather than the first few: what a
    finding does to "srv-001" it probably does to "srv-002" as well."""
    questions: int = 0
    """Its groups nothing tells apart, still to be answered."""
    settled_groups: int = 0
    """Its groups answered already, by a run or by hand."""
    conflicts: int = 0
    """The pairs of hosts it disagrees about with another finding - left out of its counts."""


def finding_summaries(result: ScanResult) -> list[FindingSummary]:
    by_finding: dict[str, list[FoundRelation]] = {finding: [] for finding in result.findings}
    for row in result.relations:
        by_finding.setdefault(row.finding, []).append(row)
    groups: dict[str, Counter[LinkOutcome]] = {finding: Counter() for finding in by_finding}
    for group in result.groups:
        groups.setdefault(group.finding, Counter())[group.outcome] += 1
    disputed: Counter[str] = Counter(
        claim.finding for conflict in result.conflicts for claim in conflict.claims
    )
    return [
        FindingSummary(
            id=finding,
            counts=outcome_counts(row.outcome for row in rows),
            samples=_spread(
                [row for row in rows if row.outcome is LinkOutcome.LINK] or rows, SAMPLE_SIZE
            ),
            questions=groups.get(finding, Counter())[LinkOutcome.UNDECIDED],
            settled_groups=groups.get(finding, Counter())[LinkOutcome.ALREADY_LINKED],
            conflicts=disputed[finding],
        )
        for finding, rows in by_finding.items()
    ]


def found_folders(result: ScanResult) -> list[str]:
    """Every folder a host of what the scan found is in."""
    return sorted(
        {
            *(folder for row in result.relations for folder in row.folders),
            *(folder for group in result.groups for folder in group.folders),
        }
    )


def _spread[T](items: Sequence[T], count: int) -> list[T]:
    """``count`` of ``items``, evenly spaced from the first to the last."""
    if len(items) <= count:
        return list(items)
    return [items[at * (len(items) - 1) // (count - 1)] for at in range(count)]


@dataclass(frozen=True, kw_only=True)
class RowFilter:
    """What the page narrows a list down to. Empty fields leave it be."""

    finding: str = ""
    outcome: LinkOutcome | None = None
    search: str = ""
    """Part of a host name, in any case."""
    folder: str = ""
    """A folder path; its subfolders are in it."""


@dataclass(frozen=True, kw_only=True)
class Page[T]:
    total: int
    """How many items match the filter, on this page and the others."""
    items: Sequence[T]


def matching_relations(rows: Sequence[FoundRelation], wanted: RowFilter) -> list[FoundRelation]:
    return [
        row
        for row in rows
        if (not wanted.finding or row.finding == wanted.finding)
        and (wanted.outcome is None or row.outcome is wanted.outcome)
        and _named(wanted.search, (row.source, row.target))
        and _in_folder(wanted.folder, row.folders)
    ]


def relations_page(
    rows: Sequence[FoundRelation], wanted: RowFilter, *, offset: int, limit: int
) -> Page[FoundRelation]:
    return _page(matching_relations(rows, wanted), offset=offset, limit=limit)


def groups_page(
    groups: Sequence[FoundGroup], wanted: RowFilter, *, offset: int, limit: int
) -> Page[FoundGroup]:
    return _page(
        [
            group
            for group in groups
            if (not wanted.finding or group.finding == wanted.finding)
            and (wanted.outcome is None or group.outcome is wanted.outcome)
            and _named(wanted.search, group.members)
            and _in_folder(wanted.folder, group.folders)
        ],
        offset=offset,
        limit=limit,
    )


def conflicts_page(
    conflicts: Sequence[FoundConflict], wanted: RowFilter, *, offset: int, limit: int
) -> Page[FoundConflict]:
    return _page(
        [
            conflict
            for conflict in conflicts
            if (not wanted.finding or any(c.finding == wanted.finding for c in conflict.claims))
            and _named(wanted.search, conflict.hosts)
            and any(_in_folder(wanted.folder, claim.folders) for claim in conflict.claims)
        ],
        offset=offset,
        limit=limit,
    )


def _page[T](items: Sequence[T], *, offset: int, limit: int) -> Page[T]:
    return Page(total=len(items), items=items[offset : offset + limit])


def _named(search: str, hosts: Iterable[str]) -> bool:
    needle = search.lower()
    return not needle or any(needle in host.lower() for host in hosts)


def _in_folder(folder: str, folders: Iterable[str]) -> bool:
    """Whether one of ``folders`` is ``folder`` or below it. The main folder holds them all."""
    return not folder or any(path == folder or path.startswith(f"{folder}/") for path in folders)


class AcceptedScan(BaseModel, frozen=True):
    """What the user made of a scan: everything it proposed, less what they took out."""

    scan_id: str
    findings: list[str]
    """The findings whose relations are stored."""
    excluded: list[str] = []
    """Relations of those findings that are not, by key."""
    answers: dict[str, str] = {}
    """Per group question, by key, the host named as the one at the deciding end."""
    resolutions: dict[str, str] = {}
    """Per conflict, by key, the claim to store, by its key."""


def accepted_pairs(result: ScanResult, accepted: AcceptedScan) -> list[tuple[str, HostPair]]:
    """Every relation ``accepted`` stands for, with the finding it came from.

    A ``ValueError`` for an answer the scan cannot have offered - a finding it did not read, a
    group or a claim it did not make, or a host that is not a member: the client is told, rather
    than something else stored.
    """
    findings = set(accepted.findings)
    if unread := sorted(findings - set(result.findings)):
        raise ValueError(f"The scan read no finding {unread[0]!r}.")
    excluded = set(accepted.excluded)
    pairs = [
        (row.finding, row.pair())
        for row in result.relations
        if row.finding in findings and row.outcome is LinkOutcome.LINK and row.key not in excluded
    ]

    groups = {group.key: group for group in result.groups}
    for key, named in accepted.answers.items():
        if (group := groups.get(key)) is None or named not in group.members:
            raise ValueError(f"The scan asked nothing that {named!r} answers: {key!r}.")
        if group.finding not in findings or group.outcome is not LinkOutcome.UNDECIDED:
            continue
        if named in group.refusals:
            raise ValueError(f"{named!r} cannot be written: {group.refusals[named]}")
        pairs.extend(
            (
                group.finding,
                HostPair(
                    source=HostName(named),
                    target=HostName(member),
                    kind_id=group.kind_id,
                    source_direction=group.direction,
                ),
            )
            for member in group.partners(named)
        )

    conflicts = {conflict.key: conflict for conflict in result.conflicts}
    for key, chosen in accepted.resolutions.items():
        claims = {claim.key: claim for claim in conflicts[key].claims} if key in conflicts else {}
        if (claim := claims.get(chosen)) is None:
            raise ValueError(f"The scan found no conflict {key!r} with a claim {chosen!r}.")
        if claim.outcome is LinkOutcome.LINK:
            pairs.append((claim.finding, claim.pair()))
    return pairs


class RunResult(BaseModel):
    """What a run did to each relation it was handed."""

    findings: list[str]
    relations: list[FoundRelation]


def run_counts(result: RunResult) -> list[tuple[str, Mapping[LinkOutcome, int]]]:
    """Per finding, what came of its relations."""
    outcomes: dict[str, list[LinkOutcome]] = {finding: [] for finding in result.findings}
    for row in result.relations:
        outcomes.setdefault(row.finding, []).append(row.outcome)
    return [(finding, outcome_counts(of_finding)) for finding, of_finding in outcomes.items()]


def failed(result: RunResult) -> list[FoundRelation]:
    """The relations a run could not store - the ones somebody has to look at."""
    return [
        row
        for row in result.relations
        if row.outcome in (LinkOutcome.NOT_WRITABLE, LinkOutcome.STORED_OTHERWISE)
    ]


_RESULT_FILE: Final = "result.json"


#: The results read last, by file and modification time. A page of a scan is asked for again
#: and again while the user looks through it, and reading fifty thousand rows is the slow part.
_READ: dict[tuple[Path, int], BaseModel] = {}
_READ_LIMIT: Final = 2


class _JsonStore[T: BaseModel]:
    def __init__(self, path: Path, model: type[T]) -> None:
        self._store = store.ObjectStore(path, serializer=store.TextSerializer())
        self._model = model

    def write(self, result: T) -> None:
        self._store.write_obj(result.model_dump_json())

    def read(self) -> T | None:
        try:
            key = (self._store.path, self._store.path.stat().st_mtime_ns)
        except FileNotFoundError:
            return None
        if isinstance(cached := _READ.get(key), self._model):
            return cached
        raw = self._store.read_obj(default="")
        if not raw:
            return None
        result = self._model.model_validate_json(raw)
        while len(_READ) >= _READ_LIMIT:
            del _READ[next(iter(_READ))]
        _READ[key] = result
        return result


def _result_store[T: BaseModel](job: BackgroundJob, model: type[T]) -> _JsonStore[T]:
    return _JsonStore(Path(job.get_work_dir(), _RESULT_FILE), model)


class UnknownJob(Exception):
    """No job of this kind with this id, or none the acting user started."""


def _own_job(job_id: str, prefix: str) -> BackgroundJob:
    """The job ``job_id``, if it is one of ``prefix`` and the logged-in user started it.

    The endpoints ask for the permission to edit hosts, not for the one to see other people's
    jobs, so they must not hand out another user's scan - or the log of any other job.
    """
    if not job_id.startswith(f"{prefix}-"):
        raise UnknownJob(job_id)
    job = BackgroundJob(job_id)
    if not job.exists() or job.get_status().user != str(user.id):
        raise UnknownJob(job_id)
    return job


def job_of(job_id: str) -> BackgroundJob:
    """A scan or a run of the logged-in user, whichever ``job_id`` names."""
    for prefix in (RelationScanBackgroundJob.job_prefix, RelationDiscoveryBackgroundJob.job_prefix):
        if job_id.startswith(f"{prefix}-"):
            return _own_job(job_id, prefix)
    raise UnknownJob(job_id)


def load_scan(job_id: str) -> ScanResult | None:
    """The scan ``job_id`` made, or ``None`` while it is still running or if it failed."""
    return _result_store(_own_job(job_id, RelationScanBackgroundJob.job_prefix), ScanResult).read()


def load_run(job_id: str) -> RunResult | None:
    """What the run ``job_id`` did, or ``None`` while it is still running or if it failed."""
    return _result_store(
        _own_job(job_id, RelationDiscoveryBackgroundJob.job_prefix), RunResult
    ).read()


def is_scan(job_id: str) -> bool:
    return job_id.startswith(f"{RelationScanBackgroundJob.job_prefix}-")


class RelationScanBackgroundJob(BackgroundJob):
    job_prefix = "relation_scan"
    # A scan is worth keeping for as long as somebody looks at it, not beyond.
    housekeeping_max_age_sec = 86400
    housekeeping_max_count = 20

    @classmethod
    @override
    def gui_title(cls) -> str:
        return _("Find relations between hosts")

    def __init__(self, job_id: str | None = None) -> None:
        super().__init__(job_id or f"{self.job_prefix}-{gen_id()}")

    def do_execute(
        self,
        findings: Sequence[FindingArgs],
        scope: Scope,
        job_interface: BackgroundProcessInterface,
        user_permission_config: UserPermissionSerializableConfig,
        tree: FolderTree,
    ) -> None:
        with job_interface.gui_context(
            UserPermissions.from_serialized_config(user_permission_config, permission_registry)
        ):
            job_interface.send_progress_update(_("Reading the hosts of Setup..."))
            evidence = evidence_of(findings)
            discovery = discover_relations(tree, evidence=evidence, acting_user=user, scope=scope)
            folders = {
                name: host.folder().path()
                for name, host in tree.root_folder().all_hosts_recursively().items()
            }
            _result_store(self, ScanResult).write(
                scan_result(
                    discovery,
                    findings=[finding.id for finding in evidence.findings],
                    folder_of=lambda name: folders.get(name, ""),
                )
            )
            job_interface.send_result_message(
                _("%(count)d hosts looked at.") % {"count": discovery.hosts_scanned}
            )


class RelationScanJobArgs(BaseModel, frozen=True):
    findings: list[FindingArgs]
    scope: ScopeArgs
    user_permission_config: UserPermissionSerializableConfig
    site_configs: SiteConfigurations
    wato_hide_folders_without_read_permissions: bool
    wato_host_attrs: Sequence[CustomHostAttrSpec]
    tags: TagConfigSpec


def relation_scan_job_entry_point(
    job_interface: BackgroundProcessInterface, args: RelationScanJobArgs
) -> None:
    RelationScanBackgroundJob(job_interface.get_job_id()).do_execute(
        args.findings,
        args.scope.scope(),
        job_interface,
        args.user_permission_config,
        FolderTree(
            config=HostsAndFoldersConfig(
                wato_hide_folders_without_read_permissions=args.wato_hide_folders_without_read_permissions,
                wato_host_attrs=args.wato_host_attrs,
                tags=TagConfig.from_config(args.tags),
                sites=args.site_configs,
            )
        ),
    )


def start_relation_scan(
    job: RelationScanBackgroundJob,
    findings: Sequence[FindingArgs],
    scope: ScopeArgs,
    user_permission_config: UserPermissionSerializableConfig,
    *,
    site_configs: SiteConfigurations,
    wato_hide_folders_without_read_permissions: bool,
    wato_host_attrs: Sequence[CustomHostAttrSpec],
    tags: TagConfigSpec,
) -> Result[None, AlreadyRunningError | StartupError]:
    """Scan in the background: a fleet of this size takes longer than a request may."""
    return job.start(
        JobTarget(
            callable=relation_scan_job_entry_point,
            args=RelationScanJobArgs(
                findings=list(findings),
                scope=scope,
                user_permission_config=user_permission_config,
                site_configs=site_configs,
                wato_hide_folders_without_read_permissions=wato_hide_folders_without_read_permissions,
                wato_host_attrs=wato_host_attrs,
                tags=tags,
            ),
        ),
        InitialStatusArgs(
            title=job.gui_title(),
            lock_wato=False,
            stoppable=False,
            user=str(user.id) if user.id else None,
        ),
    )


class RelationDiscoveryBackgroundJob(BackgroundJob):
    job_prefix = "relation_discovery"
    housekeeping_max_age_sec = 86400
    housekeeping_max_count = 20

    @classmethod
    @override
    def gui_title(cls) -> str:
        return _("Store discovered relations")

    def __init__(self, job_id: str | None = None) -> None:
        super().__init__(job_id or f"{self.job_prefix}-{gen_id()}")

    def do_execute(
        self,
        accepted: AcceptedScan,
        job_interface: BackgroundProcessInterface,
        user_permission_config: UserPermissionSerializableConfig,
        *,
        tree: FolderTree,
        pprint_value: bool,
        use_git: bool,
        activation_site_configs: SiteConfigurations,
        local_site: SiteId,
        acting_user: UserId | None,
    ) -> None:
        job_interface.send_progress_update(_("Waiting to acquire lock"))
        with (
            job_interface.gui_context(
                UserPermissions.from_serialized_config(user_permission_config, permission_registry)
            ),
            store.lock_checkmk_configuration(configuration_lockfile),
        ):
            job_interface.send_progress_update(_("Acquired lock"))
            self._do_execute(
                accepted,
                job_interface,
                tree=tree,
                pprint_value=pprint_value,
                use_git=use_git,
                activation_site_configs=activation_site_configs,
                local_site=local_site,
                acting_user=acting_user,
            )

    def _do_execute(
        self,
        accepted: AcceptedScan,
        job_interface: BackgroundProcessInterface,
        *,
        tree: FolderTree,
        pprint_value: bool,
        use_git: bool,
        activation_site_configs: SiteConfigurations,
        local_site: SiteId,
        acting_user: UserId | None,
    ) -> None:
        try:
            scanned = load_scan(accepted.scan_id)
        except UnknownJob:
            # Housekeeping may have removed the scan since the request checked it.
            scanned = None
        if scanned is None:
            job_interface.send_result_message(_("The scan is gone. Scan again."))
            return
        found = accepted_pairs(scanned, accepted)
        if not found:
            job_interface.send_result_message(_("No relation was accepted, nothing to do."))
            return

        tree.invalidate_caches()
        job_interface.send_progress_update(
            _("Storing %(count)d relations...") % {"count": len(found)}
        )
        done = 0

        def report(entry: RelationEntry) -> None:
            nonlocal done
            done += 1
            job_interface.send_progress_update(
                "[%(done)d/%(total)d] %(source)s -> %(target)s: %(outcome)s %(detail)s"
                % {
                    "done": done,
                    "total": len(found),
                    "source": entry.pair.source,
                    "target": entry.pair.target,
                    "outcome": outcome_label(entry.outcome),
                    "detail": entry.detail,
                }
            )

        entries = link_relations(
            [pair for _finding, pair in found],
            tree,
            pprint_value=pprint_value,
            pending_changes=PendingChanges(
                activation_sites=activation_site_configs,
                local_site=local_site,
                acting_user=acting_user,
                store=PendingChangesStore(),
                hooks=(
                    make_audit_log_change_hook(use_git=use_git),
                    index_update_change_hook,
                ),
            ),
            acting_user=user,
            progress=report,
        )
        _result_store(self, RunResult).write(run_result(scanned.findings, found, entries, tree))
        job_interface.send_result_message(
            _("Relation discovery finished: %(summary)s") % {"summary": run_summary(entries)}
        )


def run_result(
    findings: Sequence[str],
    found: Sequence[tuple[str, HostPair]],
    entries: Sequence[RelationEntry],
    tree: FolderTree,
) -> RunResult:
    """What a run did, per relation, with the finding each came from."""

    def folder_of(name: HostName) -> str:
        return "" if (host := tree.host(name)) is None else host.folder().path()

    return RunResult(
        findings=list(findings),
        relations=[
            _found_relation(
                RelationEntry(
                    pair=entry.pair,
                    outcome=entry.outcome,
                    finding=finding,
                    detail=entry.detail,
                ),
                folder_of,
            )
            for (finding, _pair), entry in zip(found, entries, strict=True)
        ],
    )


class RelationDiscoveryJobArgs(BaseModel, frozen=True):
    accepted: AcceptedScan
    user_permission_config: UserPermissionSerializableConfig
    site_configs: SiteConfigurations
    wato_hide_folders_without_read_permissions: bool
    wato_host_attrs: Sequence[CustomHostAttrSpec]
    tags: TagConfigSpec
    pprint_value: bool
    use_git: bool
    activation_site_configs: SiteConfigurations
    local_site: SiteId
    acting_user: AnnotatedUserId | None


def relation_discovery_job_entry_point(
    job_interface: BackgroundProcessInterface, args: RelationDiscoveryJobArgs
) -> None:
    RelationDiscoveryBackgroundJob(job_interface.get_job_id()).do_execute(
        args.accepted,
        job_interface,
        args.user_permission_config,
        tree=FolderTree(
            config=HostsAndFoldersConfig(
                wato_hide_folders_without_read_permissions=args.wato_hide_folders_without_read_permissions,
                wato_host_attrs=args.wato_host_attrs,
                tags=TagConfig.from_config(args.tags),
                sites=args.site_configs,
            )
        ),
        pprint_value=args.pprint_value,
        use_git=args.use_git,
        activation_site_configs=args.activation_site_configs,
        local_site=args.local_site,
        acting_user=args.acting_user,
    )


def start_relation_linking(
    job: RelationDiscoveryBackgroundJob,
    accepted: AcceptedScan,
    user_permission_config: UserPermissionSerializableConfig,
    *,
    site_configs: SiteConfigurations,
    wato_hide_folders_without_read_permissions: bool,
    wato_host_attrs: Sequence[CustomHostAttrSpec],
    tags: TagConfigSpec,
    pprint_value: bool,
    use_git: bool,
    activation_site_configs: SiteConfigurations,
    local_site: SiteId,
    acting_user: UserId | None,
) -> Result[None, AlreadyRunningError | StartupError]:
    """Store what the user accepted of a scan in the background, under the configuration lock."""
    return job.start(
        JobTarget(
            callable=relation_discovery_job_entry_point,
            args=RelationDiscoveryJobArgs(
                accepted=accepted,
                user_permission_config=user_permission_config,
                site_configs=site_configs,
                wato_hide_folders_without_read_permissions=wato_hide_folders_without_read_permissions,
                wato_host_attrs=wato_host_attrs,
                tags=tags,
                pprint_value=pprint_value,
                use_git=use_git,
                activation_site_configs=activation_site_configs,
                local_site=local_site,
                acting_user=acting_user,
            ),
        ),
        InitialStatusArgs(
            title=job.gui_title(),
            lock_wato=False,
            stoppable=False,
            user=str(acting_user) if acting_user else None,
        ),
    )


def register(job_registry: BackgroundJobRegistry) -> None:
    # Registered for the housekeeping, which keeps a handful of scans rather than all of them.
    job_registry.register(RelationScanBackgroundJob)
    job_registry.register(RelationDiscoveryBackgroundJob)
