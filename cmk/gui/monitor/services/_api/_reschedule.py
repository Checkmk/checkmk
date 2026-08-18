#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from datetime import datetime
from typing import Annotated

from annotated_types import Ge

from cmk.gui import sites
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
from cmk.web.utils import permission_verification as permissions

from .._commands import ServiceRescheduler
from .._impl import LiveStatusServiceActions
from .._models import RescheduleTarget
from ._family import MONITOR_SERVICES_FAMILY


@api_model
class RescheduleServiceRef:
    site_id: str = api_field(description="Site ID the service belongs to", example="local")
    host_name: str = api_field(description="Host the service belongs to", example="web-server-01")
    name: str = api_field(description="Service name", example="CPU load")


@api_model
class RescheduleServicesRequestBody:
    services: list[RescheduleServiceRef] = api_field(
        description="The services whose active checks should be rescheduled.",
    )
    spread_minutes: Annotated[int, Ge(0)] = api_field(
        description=(
            "Spread the rescheduled checks evenly over this many minutes to avoid a load spike on "
            "the monitoring server. Use 0 to reschedule all selected services immediately."
        ),
        example=5,
        default=0,
    )


@api_model
class RescheduleServicesResponse:
    rescheduled: int = api_field(
        description="Number of services for which a check was rescheduled", example=3
    )


def reschedule_checks(
    api_context: ApiContext, body: RescheduleServicesRequestBody
) -> RescheduleServicesResponse:
    """Reschedule active checks for the given services."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.reschedule")

    service_actions = LiveStatusServiceActions(connection=sites.live())

    return _handle_reschedule_checks(
        service_actions, services=body.services, spread_minutes=body.spread_minutes
    )


def _handle_reschedule_checks(
    service_actions: ServiceRescheduler,
    *,
    services: list[RescheduleServiceRef],
    spread_minutes: int,
) -> RescheduleServicesResponse:
    if not services:
        return RescheduleServicesResponse(rescheduled=0)

    now = time.time()
    targets = [
        RescheduleTarget(
            site_id=service.site_id,
            host_name=service.host_name,
            description=service.name,
            check_time=datetime.fromtimestamp(now + spread_minutes * 60.0 * index / len(services)),
        )
        for index, service in enumerate(services)
    ]
    service_actions.reschedule(targets)

    return RescheduleServicesResponse(rescheduled=len(targets))


ENDPOINT_RESCHEDULE_CHECKS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/services/actions/reschedule",
        link_relation="cmk/run",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.Perm("general.act"),
                permissions.Perm("action.reschedule"),
                # sites.live() authenticates the user, which checks these permissions.
                permissions.Perm("general.see_all"),
                permissions.OkayToIgnorePerm("bi.see_all"),
                permissions.OkayToIgnorePerm("mkeventd.seeall"),
            ]
        )
    ),
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=reschedule_checks)},
)
