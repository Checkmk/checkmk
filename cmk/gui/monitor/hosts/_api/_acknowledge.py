#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus
from typing import Annotated

from annotated_types import MinLen
from pydantic import AwareDatetime

from cmk.ccc.user import UserId
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
from cmk.gui.openapi.utils import ProblemException
from cmk.web.utils import permission_verification as permissions

from .._commands import HostAcknowledger
from .._exceptions import HostNotFoundError
from .._impl import LiveStatusHostActions
from .._models import HostTarget
from ._family import MONITOR_HOSTS_FAMILY


@api_model
class AcknowledgeHostRef:
    site_id: str = api_field(description="Site ID the host belongs to", example="local")
    name: str = api_field(description="Host name", example="web-server-01")


@api_model
class AcknowledgeRequestBody:
    hosts: list[AcknowledgeHostRef] = api_field(
        description="The hosts to acknowledge the problem of.",
    )
    comment: Annotated[str, MinLen(1)] = api_field(
        description="The comment stored with the acknowledgement.",
        example="Working on it",
    )
    sticky: bool = api_field(
        description="Keep the acknowledgement until the host is UP again.",
        example=False,
        default=False,
    )
    persistent: bool = api_field(
        description="Keep the comment after the acknowledgement ends.",
        example=False,
        default=False,
    )
    notify: bool = api_field(
        description="Notify the contacts of the hosts.", example=True, default=False
    )
    expire_on: AwareDatetime | None = api_field(
        description="When the acknowledgement ends on its own.",
        example="2026-07-21T17:32:28Z",
        default=None,
    )


@api_model
class RemoveAcknowledgementsRequestBody:
    hosts: list[AcknowledgeHostRef] = api_field(
        description="The hosts to remove the acknowledgement of.",
    )


@api_model
class AcknowledgeResponse:
    acknowledged: int = api_field(description="Number of hosts the command was sent for", example=3)


@api_model
class RemoveAcknowledgementsResponse:
    removed: int = api_field(description="Number of hosts the command was sent for", example=3)


def acknowledge(api_context: ApiContext, body: AcknowledgeRequestBody) -> AcknowledgeResponse:
    """Acknowledge the problems of the given hosts."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.acknowledge")

    return _handle_acknowledge(
        LiveStatusHostActions(connection=sites.live()), body, author=api_context.user.ident
    )


def _handle_acknowledge(
    acknowledger: HostAcknowledger, body: AcknowledgeRequestBody, *, author: UserId
) -> AcknowledgeResponse:
    targets = _targets(body.hosts)
    count = 0
    if targets:
        try:
            count = acknowledger.acknowledge(
                targets,
                author=author,
                comment=body.comment,
                sticky=body.sticky,
                persistent=body.persistent,
                notify=body.notify,
                expire_on=body.expire_on,
            )
        except HostNotFoundError:
            raise ProblemException(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                title="None of the hosts was found",
                detail="None of the hosts is monitored on the site given for it.",
            ) from None
    return AcknowledgeResponse(acknowledged=count)


def remove_acknowledgements(
    api_context: ApiContext, body: RemoveAcknowledgementsRequestBody
) -> RemoveAcknowledgementsResponse:
    """Remove the acknowledgements of the given hosts."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.acknowledge")

    return _handle_remove_acknowledgements(LiveStatusHostActions(connection=sites.live()), body)


def _handle_remove_acknowledgements(
    acknowledger: HostAcknowledger, body: RemoveAcknowledgementsRequestBody
) -> RemoveAcknowledgementsResponse:
    targets = _targets(body.hosts)
    count = 0
    if targets:
        count = acknowledger.remove_acknowledgements(targets)
    return RemoveAcknowledgementsResponse(removed=count)


def _targets(hosts: list[AcknowledgeHostRef]) -> list[HostTarget]:
    return [HostTarget(site_id=host.site_id, host_name=host.name) for host in hosts]


_PERMISSIONS = EndpointPermissions(
    required=permissions.AllPerm(
        [
            permissions.Perm("general.act"),
            permissions.Perm("action.acknowledge"),
            # sites.live() authenticates the user, which checks these permissions.
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
        ]
    )
)

ENDPOINT_ACKNOWLEDGE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/actions/acknowledge",
        link_relation="cmk/acknowledge",
        method="post",
    ),
    permissions=_PERMISSIONS,
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=acknowledge)},
)

ENDPOINT_REMOVE_ACKNOWLEDGEMENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/actions/remove_acknowledgements",
        link_relation="cmk/remove_acknowledgements",
        method="post",
    ),
    permissions=_PERMISSIONS,
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=remove_acknowledgements)},
)
