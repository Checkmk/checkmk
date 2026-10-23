#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.watolib.host_relation_scan import (
    failed,
    finding_summaries,
    found_folders,
    is_scan,
    job_of,
    load_run,
    load_scan,
    run_counts,
    UnknownJob,
)

from ._family import HOST_RELATION_DETECTION_FAMILY
from ._shared import (
    as_row_model,
    counts_model,
    need_detection_permissions,
    PERMISSIONS,
    unknown_job,
)
from .models.response_models import (
    FindingSummaryModel,
    RelationJobStatusModel,
    RunSummaryModel,
    ScanSummaryModel,
)


def show_relation_job(
    job_id: Annotated[
        str,
        PathParam(
            description="The scan, or the run storing what was accepted of one.",
            example="relation_scan-8f2a1c",
        ),
    ],
) -> RelationJobStatusModel:
    """Show how far a scan or a run has got, and what it came to

    An endpoint of its own rather than the generic background job one: that requires the
    permission to manage jobs, which somebody allowed to edit hosts need not have.
    """
    need_detection_permissions()
    try:
        snapshot = job_of(job_id).get_status_snapshot()
    except UnknownJob as exc:
        raise unknown_job(job_id) from exc

    progress = snapshot.status.loginfo["JobProgressUpdate"]
    summary = snapshot.status.loginfo["JobResult"]
    if snapshot.is_active:
        return RelationJobStatusModel(
            running=True,
            message=progress[-1] if progress else "",
            summary="",
            scan=None,
            run=None,
        )
    return RelationJobStatusModel(
        running=False,
        message=progress[-1] if progress else "",
        summary="\n".join(summary),
        scan=_scan_summary(job_id) if is_scan(job_id) else None,
        run=None if is_scan(job_id) else _run_summary(job_id),
    )


def _scan_summary(job_id: str) -> ScanSummaryModel | None:
    if (scanned := load_scan(job_id)) is None:
        return None
    return ScanSummaryModel(
        hosts_scanned=scanned.hosts_scanned,
        findings=[
            FindingSummaryModel(
                id=finding.id,
                counts=counts_model(finding.counts),
                samples=[as_row_model(row) for row in finding.samples],
                questions=finding.questions,
                settled_groups=finding.settled_groups,
                conflicts=finding.conflicts,
            )
            for finding in finding_summaries(scanned)
        ],
        conflicts=len(scanned.conflicts),
        folders=found_folders(scanned),
    )


def _run_summary(job_id: str) -> RunSummaryModel | None:
    if (done := load_run(job_id)) is None:
        return None
    return RunSummaryModel(
        findings=[
            FindingSummaryModel(
                id=finding,
                counts=counts_model(counts),
                samples=[],
                questions=0,
                settled_groups=0,
                conflicts=0,
            )
            for finding, counts in run_counts(done)
        ],
        failed=len(failed(done)),
    )


ENDPOINT_SHOW_RELATION_JOB = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("host_relation_detection", "{job_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HOST_RELATION_DETECTION_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_relation_job)},
)
