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

from .._commands import HostAttributeModifier
from .._impl import LiveStatusHostActions
from .._models import HostTarget
from ._family import MONITOR_HOSTS_FAMILY


@api_model
class ModifiedAttributeHostRef:
    site_id: str = api_field(description="Site ID the host belongs to", example="local")
    name: str = api_field(description="Host name", example="web-server-01")


@api_model
class ToggleAttributeRequestBody:
    hosts: list[ModifiedAttributeHostRef] = api_field(
        description="The hosts to enable or disable the attribute for.",
    )
    attribute: ModifiableAttribute = api_field(
        description="What to enable or disable.", example="notifications"
    )
    enabled: bool = api_field(description="Enable the attribute, else disable it.", example=False)


@api_model
class ResetModifiedAttributesRequestBody:
    hosts: list[ModifiedAttributeHostRef] = api_field(
        description="The hosts to reset the modified attributes of.",
    )


@api_model
class ModifiedAttributesResponse:
    modified: int = api_field(description="Number of hosts the command was sent for", example=3)


def toggle_attribute(
    api_context: ApiContext, body: ToggleAttributeRequestBody
) -> ModifiedAttributesResponse:
    """Enable or disable notifications, active checks or passive checks of the given hosts."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission(ATTRIBUTE_PERMISSIONS[body.attribute])

    return _handle_toggle_attribute(LiveStatusHostActions(connection=sites.live()), body)


def _handle_toggle_attribute(
    modifier: HostAttributeModifier, body: ToggleAttributeRequestBody
) -> ModifiedAttributesResponse:
    targets = _targets(body.hosts)
    if targets:
        modifier.toggle_attribute(targets, body.attribute, enabled=body.enabled)
    return ModifiedAttributesResponse(modified=len(targets))


def reset_modified_attributes(
    api_context: ApiContext, body: ResetModifiedAttributesRequestBody
) -> ModifiedAttributesResponse:
    """Reset what was enabled or disabled for the given hosts to their configuration."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.clearmodattr")

    return _handle_reset_modified_attributes(LiveStatusHostActions(connection=sites.live()), body)


def _handle_reset_modified_attributes(
    modifier: HostAttributeModifier, body: ResetModifiedAttributesRequestBody
) -> ModifiedAttributesResponse:
    targets = _targets(body.hosts)
    if targets:
        modifier.reset_modified_attributes(targets)
    return ModifiedAttributesResponse(modified=len(targets))


def _targets(hosts: list[ModifiedAttributeHostRef]) -> list[HostTarget]:
    return [HostTarget(site_id=host.site_id, host_name=host.name) for host in hosts]


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
        path="/monitor/hosts/actions/toggle_attribute",
        link_relation="cmk/toggle_attribute",
        method="post",
    ),
    permissions=_permissions(
        permissions.AnyPerm(
            [permissions.Perm(name) for name in sorted(set(ATTRIBUTE_PERMISSIONS.values()))]
        )
    ),
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=toggle_attribute)},
)

ENDPOINT_RESET_MODIFIED_ATTRIBUTES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/actions/reset_modified_attributes",
        link_relation="cmk/reset_modified_attributes",
        method="post",
    ),
    permissions=_permissions(permissions.Perm("action.clearmodattr")),
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=reset_modified_attributes)},
)
