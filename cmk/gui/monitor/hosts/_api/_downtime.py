#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus
from typing import Annotated, Self

from annotated_types import Ge, MinLen
from pydantic import AwareDatetime, model_validator

from cmk.ccc.user import UserId
from cmk.gui import sites
from cmk.gui.livestatus_utils.commands.downtimes import RecurMode
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.utils import ProblemException
from cmk.web.utils import permission_verification as permissions

from .._commands import HostDowntimeScheduler
from .._exceptions import HostNotFoundError
from .._impl import LiveStatusHostActions
from .._models import HostTarget
from ._family import MONITOR_HOSTS_FAMILY


@api_model
class DowntimeHostRef:
    site_id: str = api_field(description="Site ID the host belongs to", example="local")
    name: str = api_field(description="Host name", example="web-server-01")


@api_model
class ScheduleDowntimeRequestBody:
    hosts: list[DowntimeHostRef] = api_field(
        description="The hosts to schedule the downtime for.",
    )
    comment: Annotated[str, MinLen(1)] = api_field(
        description="The comment stored with the downtime.",
        example="Security updates",
    )
    start_time: AwareDatetime = api_field(
        description="When the downtime starts.", example="2026-07-21T17:32:28Z"
    )
    end_time: AwareDatetime = api_field(
        description="When the downtime ends.", example="2026-07-21T19:32:28Z"
    )
    recur: RecurMode = api_field(
        description="The interval the downtime repeats on, 'fixed' for none.",
        example="fixed",
        default="fixed",
    )
    duration: Annotated[int, Ge(0)] = api_field(
        description=(
            "Duration in minutes. When set, the downtime begins with the first problem within "
            "the time window rather than at its start."
        ),
        example=60,
        default=0,
    )
    include_child_hosts: bool = api_field(
        description=(
            "Also schedule the downtime for the children of the hosts, recursively, looked up "
            "on the site of each host."
        ),
        example=False,
        default=False,
    )

    @model_validator(mode="after")
    def validate_end_after_start(self) -> Self:
        if self.end_time <= self.start_time:
            raise ValueError("The downtime must end after it starts.")
        return self


@api_model
class RemoveDowntimesRequestBody:
    hosts: list[DowntimeHostRef] = api_field(
        description="The hosts to remove the downtimes of, not those of their services.",
    )


@api_model
class ScheduleDowntimeResponse:
    scheduled: int = api_field(
        description="Number of hosts the downtime was scheduled for, children included",
        example=3,
    )


@api_model
class RemoveDowntimesResponse:
    removed: int = api_field(description="Number of hosts the command was sent for", example=3)


def schedule_downtime(
    api_context: ApiContext, body: ScheduleDowntimeRequestBody
) -> ScheduleDowntimeResponse:
    """Schedule a downtime for the given hosts."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.downtimes")

    return _handle_schedule_downtime(
        LiveStatusHostActions(connection=sites.live()), body, author=api_context.user.ident
    )


def _handle_schedule_downtime(
    scheduler: HostDowntimeScheduler, body: ScheduleDowntimeRequestBody, *, author: UserId
) -> ScheduleDowntimeResponse:
    targets = _targets(body.hosts)
    if body.include_child_hosts:
        targets += scheduler.child_hosts(targets)
    count = 0
    if targets:
        try:
            count = scheduler.schedule_downtime(
                targets,
                author=author,
                comment=body.comment,
                start_time=body.start_time,
                end_time=body.end_time,
                recur=body.recur,
                duration_minutes=body.duration,
            )
        except HostNotFoundError:
            raise ProblemException(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                title="None of the hosts was found",
                detail="None of the hosts is monitored on the site given for it.",
            ) from None
    return ScheduleDowntimeResponse(scheduled=count)


def remove_downtimes(
    api_context: ApiContext, body: RemoveDowntimesRequestBody
) -> RemoveDowntimesResponse:
    """Remove the downtimes of the given hosts."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.downtimes")

    return _handle_remove_downtimes(LiveStatusHostActions(connection=sites.live()), body)


def _handle_remove_downtimes(
    scheduler: HostDowntimeScheduler, body: RemoveDowntimesRequestBody
) -> RemoveDowntimesResponse:
    targets = _targets(body.hosts)
    count = 0
    if targets:
        count = scheduler.remove_downtimes(targets)
    return RemoveDowntimesResponse(removed=count)


def _targets(hosts: list[DowntimeHostRef]) -> list[HostTarget]:
    return [HostTarget(site_id=host.site_id, host_name=host.name) for host in hosts]


_PERMISSIONS = EndpointPermissions(
    required=permissions.AllPerm(
        [
            permissions.Perm("general.act"),
            permissions.Perm("action.downtimes"),
            # sites.live() authenticates the user, which checks these permissions.
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
        ]
    )
)

ENDPOINT_SCHEDULE_DOWNTIME = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/actions/schedule_downtime",
        link_relation="cmk/schedule_downtime",
        method="post",
    ),
    permissions=_PERMISSIONS,
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=schedule_downtime)},
)

ENDPOINT_REMOVE_DOWNTIMES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/actions/remove_downtimes",
        link_relation="cmk/remove_downtimes",
        method="post",
    ),
    permissions=_PERMISSIONS,
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=remove_downtimes)},
)
