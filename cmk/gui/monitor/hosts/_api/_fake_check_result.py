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

from .._commands import HostCheckResultFaker
from .._impl import LiveStatusHostActions
from .._models import HostTarget
from ._family import MONITOR_HOSTS_FAMILY


@api_model
class FakeCheckResultHostRef:
    site_id: str = api_field(description="Site ID the host belongs to", example="local")
    name: str = api_field(description="Host name", example="web-server-01")


@api_model
class FakeCheckResultRequestBody:
    hosts: list[FakeCheckResultHostRef] = api_field(
        description="The hosts to submit the check result for.",
    )
    state: Literal[0, 1] = api_field(description="The state, 0 for UP and 1 for DOWN.", example=1)
    plugin_output: str = api_field(
        description="The output of the check. Without one, it names the state and who set it.",
        example="Testing the notification of a down host",
        default="",
    )
    metrics: str = api_field(
        description="Metrics in the format of the performance data of a check.",
        example="rta=0.5ms;200;500;0",
        default="",
    )


@api_model
class FakeCheckResultResponse:
    faked: int = api_field(
        description="Number of hosts for which a check result was submitted", example=3
    )


def fake_check_result(
    api_context: ApiContext, body: FakeCheckResultRequestBody
) -> FakeCheckResultResponse:
    """Submit a check result for the given hosts, as if their check had run."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.fakechecks")

    return _handle_fake_check_result(
        LiveStatusHostActions(connection=sites.live()), body, author=api_context.user.ident
    )


def _handle_fake_check_result(
    faker: HostCheckResultFaker, body: FakeCheckResultRequestBody, *, author: UserId
) -> FakeCheckResultResponse:
    targets = [HostTarget(site_id=host.site_id, host_name=host.name) for host in body.hosts]
    if targets:
        faker.fake_check_result(
            targets,
            state=body.state,
            output=fake_check_output(
                output=body.plugin_output,
                metrics=body.metrics,
                state_title=(_("Up"), _("Down"))[body.state],
                author=author,
            ),
        )
    return FakeCheckResultResponse(faked=len(targets))


ENDPOINT_FAKE_CHECK_RESULT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/actions/fake_check_result",
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
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=fake_check_result)},
)
