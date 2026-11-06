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

from .._commands import ServiceAcknowledger
from .._exceptions import ServiceNotFoundError
from .._impl import LiveStatusServiceActions
from .._models import ServiceTarget
from ._family import MONITOR_SERVICES_FAMILY


@api_model
class AcknowledgeServiceRef:
    site_id: str = api_field(description="Site ID the service belongs to", example="local")
    host_name: str = api_field(description="Host the service belongs to", example="web-server-01")
    name: str = api_field(description="Service name", example="CPU load")


@api_model
class AcknowledgeServicesRequestBody:
    services: list[AcknowledgeServiceRef] = api_field(
        description="The services to acknowledge the problem of.",
    )
    comment: Annotated[str, MinLen(1)] = api_field(
        description="The comment stored with the acknowledgement.",
        example="Working on it",
    )
    sticky: bool = api_field(
        description="Keep the acknowledgement until the service is OK again.",
        example=False,
        default=False,
    )
    persistent: bool = api_field(
        description="Keep the comment after the acknowledgement ends.",
        example=False,
        default=False,
    )
    notify: bool = api_field(
        description="Notify the contacts of the services.", example=True, default=False
    )
    expire_on: AwareDatetime | None = api_field(
        description="When the acknowledgement ends on its own.",
        example="2026-07-21T17:32:28Z",
        default=None,
    )


@api_model
class RemoveAcknowledgementsServicesRequestBody:
    services: list[AcknowledgeServiceRef] = api_field(
        description="The services to remove the acknowledgement of.",
    )


@api_model
class AcknowledgeServicesResponse:
    acknowledged: int = api_field(
        description="Number of services the command was sent for, those in state OK left out",
        example=3,
    )


@api_model
class RemoveAcknowledgementsServicesResponse:
    removed: int = api_field(description="Number of services the command was sent for", example=3)


def acknowledge(
    api_context: ApiContext, body: AcknowledgeServicesRequestBody
) -> AcknowledgeServicesResponse:
    """Acknowledge the problems of the given services."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.acknowledge")

    return _handle_acknowledge(
        LiveStatusServiceActions(connection=sites.live()), body, author=api_context.user.ident
    )


def _handle_acknowledge(
    acknowledger: ServiceAcknowledger, body: AcknowledgeServicesRequestBody, *, author: UserId
) -> AcknowledgeServicesResponse:
    targets = _targets(body.services)
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
        except ServiceNotFoundError:
            raise ProblemException(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                title="None of the services was found",
                detail="None of the services is monitored on the site given for it.",
            ) from None
    return AcknowledgeServicesResponse(acknowledged=count)


def remove_acknowledgements(
    api_context: ApiContext, body: RemoveAcknowledgementsServicesRequestBody
) -> RemoveAcknowledgementsServicesResponse:
    """Remove the acknowledgements of the given services."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.acknowledge")

    return _handle_remove_acknowledgements(LiveStatusServiceActions(connection=sites.live()), body)


def _handle_remove_acknowledgements(
    acknowledger: ServiceAcknowledger, body: RemoveAcknowledgementsServicesRequestBody
) -> RemoveAcknowledgementsServicesResponse:
    targets = _targets(body.services)
    count = 0
    if targets:
        count = acknowledger.remove_acknowledgements(targets)
    return RemoveAcknowledgementsServicesResponse(removed=count)


def _targets(services: list[AcknowledgeServiceRef]) -> list[ServiceTarget]:
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
        path="/monitor/services/actions/acknowledge",
        link_relation="cmk/acknowledge",
        method="post",
    ),
    permissions=_PERMISSIONS,
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=acknowledge)},
)

ENDPOINT_REMOVE_ACKNOWLEDGEMENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/services/actions/remove_acknowledgements",
        link_relation="cmk/remove_acknowledgements",
        method="post",
    ),
    permissions=_PERMISSIONS,
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=remove_acknowledgements)},
)
