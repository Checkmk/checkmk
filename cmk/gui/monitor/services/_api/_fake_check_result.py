#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.ccc.user import UserId
from cmk.gui import sites
from cmk.gui.i18n import _
from cmk.gui.monitor.command import fake_check_output
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

from .._commands import ServiceCheckResultFaker
from .._impl import LiveStatusServiceActions
from .._models import ServiceTarget
from ._family import MONITOR_SERVICES_FAMILY


@api_model
class FakeCheckResultServiceRef:
    site_id: str = api_field(description="Site ID the service belongs to", example="local")
    host_name: str = api_field(description="Host the service belongs to", example="web-server-01")
    name: str = api_field(description="Service name", example="CPU load")


@api_model
class FakeCheckResultServicesRequestBody:
    services: list[FakeCheckResultServiceRef] = api_field(
        description="The services to submit the check result for.",
    )
    state: Literal[0, 1, 2, 3] = api_field(
        description="The state, 0 for OK, 1 for WARN, 2 for CRIT and 3 for UNKNOWN.", example=2
    )
    plugin_output: str = api_field(
        description="The output of the check. Without one, it names the state and who set it.",
        example="Testing the notification of a critical service",
        default="",
    )
    metrics: str = api_field(
        description="Metrics in the format of the performance data of a check.",
        example="load1=5;10;20",
        default="",
    )


@api_model
class FakeCheckResultServicesResponse:
    faked: int = api_field(
        description="Number of services for which a check result was submitted", example=3
    )


def fake_check_result(
    api_context: ApiContext, body: FakeCheckResultServicesRequestBody
) -> FakeCheckResultServicesResponse:
    """Submit a check result for the given services, as if their check had run."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.fakechecks")

    return _handle_fake_check_result(
        LiveStatusServiceActions(connection=sites.live()), body, author=api_context.user.ident
    )


def _handle_fake_check_result(
    faker: ServiceCheckResultFaker, body: FakeCheckResultServicesRequestBody, *, author: UserId
) -> FakeCheckResultServicesResponse:
    targets = [
        ServiceTarget(
            site_id=service.site_id, host_name=service.host_name, description=service.name
        )
        for service in body.services
    ]
    if targets:
        faker.fake_check_result(
            targets,
            state=body.state,
            output=fake_check_output(
                output=body.plugin_output,
                metrics=body.metrics,
                state_title=(_("OK"), _("Warning"), _("Critical"), _("Unknown"))[body.state],
                author=author,
            ),
        )
    return FakeCheckResultServicesResponse(faked=len(targets))


ENDPOINT_FAKE_CHECK_RESULT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/services/actions/fake_check_result",
        link_relation="cmk/fake_check_result",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.Perm("general.act"),
                permissions.Perm("action.fakechecks"),
                # sites.live() authenticates the user, which checks these permissions.
                permissions.Perm("general.see_all"),
                permissions.OkayToIgnorePerm("bi.see_all"),
                permissions.OkayToIgnorePerm("mkeventd.seeall"),
            ]
        )
    ),
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=fake_check_result)},
)
