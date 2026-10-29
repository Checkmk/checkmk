#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import sites
from cmk.gui.monitor.command import ATTRIBUTE_PERMISSIONS, ModifiableAttribute
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

from .._commands import ServiceAttributeModifier
from .._impl import LiveStatusServiceActions
from .._models import ServiceTarget
from ._family import MONITOR_SERVICES_FAMILY


@api_model
class ModifiedAttributeServiceRef:
    site_id: str = api_field(description="Site ID the service belongs to", example="local")
    host_name: str = api_field(description="Host the service belongs to", example="web-server-01")
    name: str = api_field(description="Service name", example="CPU load")


@api_model
class ToggleAttributeServicesRequestBody:
    services: list[ModifiedAttributeServiceRef] = api_field(
        description="The services to enable or disable the attribute for.",
    )
    attribute: ModifiableAttribute = api_field(
        description="What to enable or disable.", example="notifications"
    )
    enabled: bool = api_field(description="Enable the attribute, else disable it.", example=False)


@api_model
class ResetModifiedAttributesServicesRequestBody:
    services: list[ModifiedAttributeServiceRef] = api_field(
        description="The services to reset the modified attributes of.",
    )


@api_model
class ModifiedAttributesServicesResponse:
    modified: int = api_field(description="Number of services the command was sent for", example=3)


def toggle_attribute(
    api_context: ApiContext, body: ToggleAttributeServicesRequestBody
) -> ModifiedAttributesServicesResponse:
    """Enable or disable notifications, active checks or passive checks of the given services."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission(ATTRIBUTE_PERMISSIONS[body.attribute])

    return _handle_toggle_attribute(LiveStatusServiceActions(connection=sites.live()), body)


def _handle_toggle_attribute(
    modifier: ServiceAttributeModifier, body: ToggleAttributeServicesRequestBody
) -> ModifiedAttributesServicesResponse:
    targets = _targets(body.services)
    if targets:
        modifier.toggle_attribute(targets, body.attribute, enabled=body.enabled)
    return ModifiedAttributesServicesResponse(modified=len(targets))


def reset_modified_attributes(
    api_context: ApiContext, body: ResetModifiedAttributesServicesRequestBody
) -> ModifiedAttributesServicesResponse:
    """Reset what was enabled or disabled for the given services to their configuration."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.clearmodattr")

    return _handle_reset_modified_attributes(
        LiveStatusServiceActions(connection=sites.live()), body
    )


def _handle_reset_modified_attributes(
    modifier: ServiceAttributeModifier, body: ResetModifiedAttributesServicesRequestBody
) -> ModifiedAttributesServicesResponse:
    targets = _targets(body.services)
    if targets:
        modifier.reset_modified_attributes(targets)
    return ModifiedAttributesServicesResponse(modified=len(targets))


def _targets(services: list[ModifiedAttributeServiceRef]) -> list[ServiceTarget]:
    return [
        ServiceTarget(
            site_id=service.site_id, host_name=service.host_name, description=service.name
        )
        for service in services
    ]


def _permissions(*required: permissions.BasePerm) -> EndpointPermissions:
    return EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.Perm("general.act"),
                *required,
                # sites.live() authenticates the user, which checks these permissions.
                permissions.Perm("general.see_all"),
                permissions.OkayToIgnorePerm("bi.see_all"),
                permissions.OkayToIgnorePerm("mkeventd.seeall"),
            ]
        )
    )


ENDPOINT_TOGGLE_ATTRIBUTE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/services/actions/toggle_attribute",
        link_relation="cmk/toggle_attribute",
        method="post",
    ),
    permissions=_permissions(
        permissions.AnyPerm(
            [permissions.Perm(name) for name in sorted(set(ATTRIBUTE_PERMISSIONS.values()))]
        )
    ),
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=toggle_attribute)},
)

ENDPOINT_RESET_MODIFIED_ATTRIBUTES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/services/actions/reset_modified_attributes",
        link_relation="cmk/reset_modified_attributes",
        method="post",
    ),
    permissions=_permissions(permissions.Perm("action.clearmodattr")),
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=reset_modified_attributes)},
)
