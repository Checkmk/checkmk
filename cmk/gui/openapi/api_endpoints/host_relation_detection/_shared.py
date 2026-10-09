#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What the detection endpoints have in common."""

from collections.abc import Collection, Mapping
from http import HTTPStatus
from typing import assert_never

from cmk.ccc.hostaddress import HostName
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.host_config._utils import rw_permissions
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.user_sites import get_configured_site_choices
from cmk.gui.utils.host_relation_kinds import is_name_token
from cmk.gui.watolib.host_relation_detection import (
    LinkOutcome,
    NamesTellApart,
    SharedAttribute,
    SharedLabel,
    Suggestions,
    TellApart,
    ValueTellsApart,
)
from cmk.gui.watolib.host_relation_scan import (
    evidence_of,
    FindingArgs,
    FoundConflict,
    FoundGroup,
    FoundReason,
    FoundRelation,
    MarkArgs,
    ScopeArgs,
    value_source,
    ValueArgs,
)
from cmk.gui.watolib.host_relations import relation_choice_name
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.web.utils import permission_verification as permissions

from .models.request_models import (
    HostValueModel,
    ScanRequestModel,
    ScopeModel,
    SuggestEvidenceRequestModel,
)
from .models.response_models import (
    RelationConflictModel,
    RelationGroupModel,
    RelationReasonModel,
    RelationRowModel,
    SuggestionsModel,
    ToldApartModel,
    ValueCountModel,
    ValueExampleModel,
    ValueFindingModel,
    WordExampleModel,
    WordFindingModel,
)

#: Storing a detected relation is editing hosts, and nothing beyond it - hence no permission
#: of its own, and the ones the host-writing endpoints declare. Finding relations asks for the
#: same, as in the service discovery.
PERMISSIONS = rw_permissions(
    permissions.Perm("wato.edit"),
    permissions.Perm("wato.hosts"),
    permissions.Perm("wato.edit_hosts"),
    # Read when the state of a job is shown: whether the user may delete it.
    permissions.Optional(permissions.Perm("background_jobs.delete_jobs")),
)


def need_detection_permissions() -> None:
    user.need_permission("wato.edit")
    user.need_permission("wato.hosts")
    user.need_permission("wato.edit_hosts")


def finding_args(body: ScanRequestModel, custom_attributes: Collection[str]) -> list[FindingArgs]:
    """What the page asked the scan to read, or a 400 naming the finding at fault.

    Checked here rather than left to the job, so that the page hears about it in the answer
    to its request and not in the log of a job that failed.
    """
    for finding in body.findings:
        for value in (finding.marked_by, finding.paired_by):
            if not isinstance(value, ApiOmitted):
                _need_offered_value(value.source, value.name, custom_attributes)
    found = [
        FindingArgs(
            id=finding.id,
            kind_id=finding.kind,
            words=finding.words,
            marked_by=(
                None
                if isinstance(finding.marked_by, ApiOmitted)
                else MarkArgs(
                    source=finding.marked_by.source,
                    name=finding.marked_by.name,
                    value=finding.marked_by.value,
                )
            ),
            paired_by=_value_args(finding.paired_by),
        )
        for finding in body.findings
    ]
    if len({finding.id for finding in found}) != len(found):
        raise invalid_request("Every finding needs an id of its own.")
    try:
        evidence_of(found)
    except ValueError as exc:
        raise invalid_request(str(exc)) from exc
    return found


def _value_args(model: HostValueModel | ApiOmitted) -> ValueArgs | None:
    if isinstance(model, ApiOmitted):
        return None
    return ValueArgs(source=model.source, name=model.name)


def parsed_words(body: SuggestEvidenceRequestModel) -> list[str]:
    """The words the user typed, or a 400 for one no host name could ever carry."""
    for word in body.words:
        if not is_name_token(word):
            raise invalid_request(f"{word!r} cannot be read out of a host name.")
    return body.words


def parsed_values(
    body: SuggestEvidenceRequestModel, custom_attributes: Collection[str]
) -> list[SharedLabel | SharedAttribute]:
    for value in body.values:
        _need_offered_value(value.source, value.name, custom_attributes)
    return [ValueArgs(source=value.source, name=value.name).where() for value in body.values]


def _need_offered_value(source: str, name: str, custom_attributes: Collection[str]) -> None:
    """The built-in attributes (address, alias, ...) tell how a host is monitored, not which
    machine it is."""
    if source == "attribute" and name not in custom_attributes:
        raise invalid_request(f"{name!r} is not a custom host attribute.")


def parsed_scope(tree: FolderTree, model: ScopeModel | ApiOmitted) -> ScopeArgs:
    """Where the page asked to look, or a 400 for a folder or site the page would not offer.

    Asked against the very choices the page offers, so the two cannot disagree.
    """
    if isinstance(model, ApiOmitted):
        return ScopeArgs()
    folder = "" if isinstance(model.folder, ApiOmitted) else model.folder.path()
    if folder not in dict(tree.folder_choices_fulltitle(user)):
        raise invalid_request(f"The folder {'/' + folder!r} cannot be looked in.")
    site = None if isinstance(model.site, ApiOmitted) else model.site
    if site is not None and site not in dict(get_configured_site_choices()):
        raise invalid_request(f"The site {site!r} cannot be looked in.")
    return ScopeArgs(folder=folder, site=site)


def invalid_request(detail: str) -> ProblemException:
    return ProblemException(status=HTTPStatus.BAD_REQUEST, title="Invalid request", detail=detail)


def unknown_job(job_id: str) -> ProblemException:
    return ProblemException(
        status=HTTPStatus.NOT_FOUND,
        title="Unknown scan or run",
        detail=f"There is no relation detection scan or run of yours with the ID '{job_id}'.",
    )


def counts_model(counts: Mapping[LinkOutcome, int]) -> dict[str, int]:
    return {outcome.value: count for outcome, count in counts.items()}


def _reason_model(reason: FoundReason) -> RelationReasonModel:
    return RelationReasonModel(
        word=reason.word, source=reason.source, name=reason.name, value=reason.value
    )


def as_row_model(row: FoundRelation) -> RelationRowModel:
    return RelationRowModel(
        key=row.key,
        finding=row.finding,
        source_host=HostName(row.source),
        target_host=HostName(row.target),
        kind=row.kind_id,
        relation=relation_choice_name(row.kind_id, row.source_direction),
        folders=list(row.folders),
        evidence=row.evidence,
        reason=None if row.reason is None else _reason_model(row.reason),
        outcome=row.outcome,
        detail=row.detail,
    )


def as_group_model(group: FoundGroup) -> RelationGroupModel:
    return RelationGroupModel(
        key=group.key,
        finding=group.finding,
        kind=group.kind_id,
        relation=relation_choice_name(group.kind_id, group.direction),
        members=[HostName(member) for member in group.members],
        folders=list(group.folders),
        evidence=group.evidence,
        reason=_reason_model(group.reason),
        outcome=group.outcome,
        settled=None if group.settled is None else HostName(group.settled),
        refusals=dict(group.refusals),
        partners={
            member: [HostName(partner) for partner in group.partners(member)]
            for member in group.members
        },
    )


def as_conflict_model(conflict: FoundConflict) -> RelationConflictModel:
    return RelationConflictModel(
        key=conflict.key,
        hosts=[HostName(host) for host in conflict.hosts],
        claims=[as_row_model(claim) for claim in conflict.claims],
    )


def _told_apart_model(told_apart: TellApart) -> ToldApartModel | None:
    match told_apart:
        case None:
            return None
        case NamesTellApart(kind_id=kind_id, words=words, groups=groups):
            return ToldApartModel(
                by="names",
                kind=kind_id,
                words=list(words),
                groups=groups,
                source=None,
                name=None,
                values=[],
                suggested=None,
            )
        case ValueTellsApart(where=where, values=values, suggested=suggested):
            return ToldApartModel(
                by="value",
                kind=None,
                words=[],
                groups=0,
                source=value_source(where),
                name=where.name,
                values=[ValueCountModel(value=value, groups=groups) for value, groups in values],
                suggested=suggested,
            )
        case _:
            assert_never(told_apart)


def as_suggestions_model(found: Suggestions) -> SuggestionsModel:
    return SuggestionsModel(
        hosts_scanned=found.hosts_scanned,
        words=[
            WordFindingModel(
                word=finding.word,
                pairs=finding.pairs,
                examples=[
                    WordExampleModel(named=named, base=base) for named, base in finding.examples
                ],
                kind=finding.kind_id,
            )
            for finding in found.words
        ],
        values=[
            ValueFindingModel(
                source=value_source(finding.where),
                name=finding.where.name,
                groups=finding.groups,
                largest_group=finding.largest_group,
                examples=[
                    ValueExampleModel(
                        value=example.value, hosts=list(example.hosts), size=example.size
                    )
                    for example in finding.examples
                ],
                too_wide=finding.too_wide,
                told_apart=_told_apart_model(finding.told_apart),
            )
            for finding in found.values
        ],
        label_names=list(found.label_names),
        attribute_names=list(found.attribute_names),
    )
