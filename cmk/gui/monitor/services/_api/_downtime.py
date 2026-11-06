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

from .._commands import ServiceDowntimeScheduler
from .._exceptions import ServiceNotFoundError
from .._impl import LiveStatusServiceActions
from .._models import ServiceTarget
from ._family import MONITOR_SERVICES_FAMILY


@api_model
class DowntimeServiceRef:
    site_id: str = api_field(description="Site ID the service belongs to", example="local")
    host_name: str = api_field(description="Host the service belongs to", example="web-server-01")
    name: str = api_field(description="Service name", example="CPU load")


@api_model
class ScheduleDowntimeServicesRequestBody:
    services: list[DowntimeServiceRef] = api_field(
        description="The services to schedule the downtime for.",
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

    @model_validator(mode="after")
    def validate_end_after_start(self) -> Self:
        if self.end_time <= self.start_time:
            raise ValueError("The downtime must end after it starts.")
        return self


@api_model
class RemoveDowntimesServicesRequestBody:
    services: list[DowntimeServiceRef] = api_field(
        description="The services to remove the downtimes of.",
    )


@api_model
class ScheduleDowntimeServicesResponse:
    scheduled: int = api_field(
        description="Number of services the downtime was scheduled for",
        example=3,
    )


@api_model
class RemoveDowntimesServicesResponse:
    removed: int = api_field(description="Number of services the command was sent for", example=3)


def schedule_downtime(
    api_context: ApiContext, body: ScheduleDowntimeServicesRequestBody
) -> ScheduleDowntimeServicesResponse:
    """Schedule a downtime for the given services."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.downtimes")

    return _handle_schedule_downtime(
        LiveStatusServiceActions(connection=sites.live()), body, author=api_context.user.ident
    )


def _handle_schedule_downtime(
    scheduler: ServiceDowntimeScheduler,
    body: ScheduleDowntimeServicesRequestBody,
    *,
    author: UserId,
) -> ScheduleDowntimeServicesResponse:
    targets = _targets(body.services)
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
        except ServiceNotFoundError:
            raise ProblemException(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                title="None of the services was found",
                detail="None of the services is monitored on the site given for it.",
            ) from None
    return ScheduleDowntimeServicesResponse(scheduled=count)


def remove_downtimes(
    api_context: ApiContext, body: RemoveDowntimesServicesRequestBody
) -> RemoveDowntimesServicesResponse:
    """Remove the downtimes of the given services."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.downtimes")

    return _handle_remove_downtimes(LiveStatusServiceActions(connection=sites.live()), body)


def _handle_remove_downtimes(
    scheduler: ServiceDowntimeScheduler, body: RemoveDowntimesServicesRequestBody
) -> RemoveDowntimesServicesResponse:
    targets = _targets(body.services)
    count = 0
    if targets:
        count = scheduler.remove_downtimes(targets)
    return RemoveDowntimesServicesResponse(removed=count)


def _targets(services: list[DowntimeServiceRef]) -> list[ServiceTarget]:
    return [
        ServiceTarget(
            site_id=service.site_id, host_name=service.host_name, description=service.name
        )
        for service in services
    ]


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
        path="/monitor/services/actions/schedule_downtime",
        link_relation="cmk/schedule_downtime",
        method="post",
    ),
    permissions=_PERMISSIONS,
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=schedule_downtime)},
)

ENDPOINT_REMOVE_DOWNTIMES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/services/actions/remove_downtimes",
        link_relation="cmk/remove_downtimes",
        method="post",
    ),
    permissions=_PERMISSIONS,
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=remove_downtimes)},
)
