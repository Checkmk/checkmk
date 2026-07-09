#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from datetime import datetime
from typing import Annotated

from annotated_types import Ge

from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.utils import permission_verification as permissions

from .._commands import HostRescheduler
from .._impl import LiveStatusHostActions
from .._models import RescheduleTarget
from ._family import MONITOR_HOSTS_FAMILY


@api_model
class RescheduleHostRef:
    site_id: str = api_field(description="Site ID the host belongs to", example="local")
    name: str = api_field(description="Host name", example="web-server-01")


@api_model
class RescheduleRequestBody:
    hosts: list[RescheduleHostRef] = api_field(
        description="The hosts whose active checks should be rescheduled.",
    )
    spread_minutes: Annotated[int, Ge(0)] = api_field(
        description=(
            "Spread the rescheduled checks evenly over this many minutes to avoid a load spike on "
            "the monitoring server. Use 0 to reschedule all selected hosts immediately."
        ),
        example=5,
        default=0,
    )


@api_model
class RescheduleResponse:
    rescheduled: int = api_field(
        description="Number of hosts for which a check was rescheduled", example=3
    )


def reschedule_checks(body: RescheduleRequestBody) -> RescheduleResponse:
    """Reschedule active checks for the given hosts."""
    user.need_permission("general.act")
    user.need_permission("action.reschedule")

    host_actions = LiveStatusHostActions(connection=sites.live())

    return _handle_reschedule_checks(
        host_actions, hosts=body.hosts, spread_minutes=body.spread_minutes
    )


def _handle_reschedule_checks(
    host_actions: HostRescheduler,
    *,
    hosts: list[RescheduleHostRef],
    spread_minutes: int,
) -> RescheduleResponse:
    if not hosts:
        return RescheduleResponse(rescheduled=0)

    now = time.time()
    targets = [
        RescheduleTarget(
            site_id=host.site_id,
            host_name=host.name,
            check_time=datetime.fromtimestamp(now + spread_minutes * 60.0 * index / len(hosts)),
        )
        for index, host in enumerate(hosts)
    ]
    host_actions.reschedule(targets)

    return RescheduleResponse(rescheduled=len(targets))


ENDPOINT_RESCHEDULE_CHECKS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/actions/reschedule",
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
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=reschedule_checks)},
)
