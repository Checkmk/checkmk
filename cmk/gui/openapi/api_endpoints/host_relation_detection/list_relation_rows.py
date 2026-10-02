#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus
from typing import Annotated, Literal

from annotated_types import Ge, Le

from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_object_collection_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.host_relation_detection import LinkOutcome
from cmk.gui.watolib.host_relation_scan import (
    conflicts_page,
    failed,
    groups_page,
    is_scan,
    load_run,
    load_scan,
    matching_relations,
    relations_page,
    RowFilter,
    UnknownJob,
)

from ._family import HOST_RELATION_DETECTION_FAMILY
from ._shared import (
    as_conflict_model,
    as_group_model,
    as_row_model,
    need_detection_permissions,
    PERMISSIONS,
    unknown_job,
)
from .models.response_models import (
    RelationConflictModel,
    RelationGroupModel,
    RelationRowModel,
    RowsPageModel,
)


def list_relation_rows(
    job_id: Annotated[
        str,
        PathParam(
            description="The scan, or the run storing what was accepted of one.",
            example="relation_scan-8f2a1c",
        ),
    ],
    part: Annotated[
        Literal["relations", "groups", "conflicts", "failed"],
        QueryParam(
            description="What to list: the relations a scan proposes, the groups it can only "
            "ask about, the pairs of hosts its findings disagree about - or, for a run, the "
            "relations it could not store.",
            example="relations",
        ),
    ] = "relations",
    finding: Annotated[
        str, QueryParam(description="Only rows of this finding.", example="word:ilo")
    ] = "",
    outcome: Annotated[
        LinkOutcome | None, QueryParam(description="Only rows with this outcome.", example="link")
    ] = None,
    search: Annotated[
        str,
        QueryParam(description="Only rows with a host whose name has this in it.", example="srv"),
    ] = "",
    folder: Annotated[
        str,
        QueryParam(
            description="Only rows with a host in this folder or below it, by path.",
            example="datacenter/linux",
        ),
    ] = "",
    offset: Annotated[
        Annotated[int, Ge(0)], QueryParam(description="How many rows to skip.", example="0")
    ] = 0,
    limit: Annotated[
        Annotated[int, Ge(1), Le(500)],
        QueryParam(description="How many rows to return at most.", example="100"),
    ] = 100,
    all_keys: Annotated[
        bool,
        QueryParam(
            description="Also return the key of every relation that matches and can be stored, "
            "on all pages - to take all of them out of a run at once.",
            example="false",
        ),
    ] = False,
) -> RowsPageModel:
    """Show one page of what a scan found, or of what a run could not store

    A fleet proposes more relations than a page can show at once, so they are read a page at
    a time, narrowed down to a finding, an outcome, a host or a folder.
    """
    need_detection_permissions()
    wanted = RowFilter(finding=finding, outcome=outcome, search=search, folder=folder)
    try:
        if not is_scan(job_id):
            if part != "failed":
                raise ProblemException(
                    status=HTTPStatus.BAD_REQUEST,
                    title="Invalid request",
                    detail="A run lists what failed only.",
                )
            if (done := load_run(job_id)) is None:
                raise _not_finished()
            page = relations_page(failed(done), wanted, offset=offset, limit=limit)
            return _page(page.total, relations=[as_row_model(row) for row in page.items])
        if (scanned := load_scan(job_id)) is None:
            raise _not_finished()
    except UnknownJob as exc:
        raise unknown_job(job_id) from exc

    match part:
        case "relations":
            found = relations_page(scanned.relations, wanted, offset=offset, limit=limit)
            return _page(
                found.total,
                relations=[as_row_model(row) for row in found.items],
                keys=(
                    [
                        row.key
                        for row in matching_relations(scanned.relations, wanted)
                        if row.outcome is LinkOutcome.LINK
                    ]
                    if all_keys
                    else None
                ),
            )
        case "groups":
            asked = groups_page(scanned.groups, wanted, offset=offset, limit=limit)
            return _page(asked.total, groups=[as_group_model(group) for group in asked.items])
        case "conflicts":
            disputed = conflicts_page(scanned.conflicts, wanted, offset=offset, limit=limit)
            return _page(
                disputed.total,
                conflicts=[as_conflict_model(conflict) for conflict in disputed.items],
            )
        case "failed":
            raise ProblemException(
                status=HTTPStatus.BAD_REQUEST,
                title="Invalid request",
                detail="A scan has not stored anything.",
            )


def _page(
    total: int,
    *,
    relations: list[RelationRowModel] | None = None,
    groups: list[RelationGroupModel] | None = None,
    conflicts: list[RelationConflictModel] | None = None,
    keys: list[str] | None = None,
) -> RowsPageModel:
    return RowsPageModel(
        total=total,
        relations=relations or [],
        groups=groups or [],
        conflicts=conflicts or [],
        keys=keys or [],
    )


def _not_finished() -> ProblemException:
    return ProblemException(
        status=HTTPStatus.CONFLICT,
        title="Not finished yet",
        detail="Ask again once the job has finished.",
    )


ENDPOINT_LIST_RELATION_ROWS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_object_collection_href("host_relation_detection", "{job_id}", "rows"),
        link_relation="cmk/list",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HOST_RELATION_DETECTION_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_relation_rows)},
)
