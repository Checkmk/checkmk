#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from annotated_types import MinLen

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
from cmk.web.utils import permission_verification as permissions

from .._commands import ServiceNotifier
from .._impl import LiveStatusServiceActions
from .._models import ServiceTarget
from ._family import MONITOR_SERVICES_FAMILY


@api_model
class CustomNotificationServiceRef:
    site_id: str = api_field(description="Site ID the service belongs to", example="local")
    host_name: str = api_field(description="Host the service belongs to", example="web-server-01")
    name: str = api_field(description="Service name", example="CPU load")


@api_model
class CustomNotificationServicesRequestBody:
    services: list[CustomNotificationServiceRef] = api_field(
        description="The services to send a custom notification for.",
    )
    comment: Annotated[str, MinLen(1)] = api_field(
        description="The message the notification carries.",
        example="Testing the notification setup",
    )
    forced: bool = api_field(
        description=(
            "Send regardless of restrictions, e.g. the notification period or disabled "
            "notifications."
        ),
        example=False,
        default=False,
    )
    broadcast: bool = api_field(
        description="Send to all contacts of the services.",
        example=False,
        default=False,
    )


@api_model
class CustomNotificationServicesResponse:
    notified: int = api_field(
        description="Number of services for which a notification was sent", example=3
    )


def send_custom_notification(
    api_context: ApiContext, body: CustomNotificationServicesRequestBody
) -> CustomNotificationServicesResponse:
    """Send a custom notification for the given services."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.customnotification")

    return _handle_custom_notification(
        LiveStatusServiceActions(connection=sites.live()),
        body,
        author=api_context.user.ident,
    )


def _handle_custom_notification(
    notifier: ServiceNotifier, body: CustomNotificationServicesRequestBody, *, author: UserId
) -> CustomNotificationServicesResponse:
    targets = [
        ServiceTarget(
            site_id=service.site_id, host_name=service.host_name, description=service.name
        )
        for service in body.services
    ]
    if targets:
        notifier.send_custom_notification(
            targets,
            author=author,
            comment=body.comment,
            forced=body.forced,
            broadcast=body.broadcast,
        )
    return CustomNotificationServicesResponse(notified=len(targets))


ENDPOINT_SEND_CUSTOM_NOTIFICATION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/services/actions/custom_notification",
        link_relation="cmk/send_custom_notification",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.Perm("general.act"),
                permissions.Perm("action.customnotification"),
                # sites.live() authenticates the user, which checks these permissions.
                permissions.Perm("general.see_all"),
                permissions.OkayToIgnorePerm("bi.see_all"),
                permissions.OkayToIgnorePerm("mkeventd.seeall"),
            ]
        )
    ),
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=send_custom_notification)},
)
