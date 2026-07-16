#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Per-host action menu for the all-hosts monitoring view.

This exposes the legacy "host icons" action menu (the entries behind the three-dots
button in a view row) as typed JSON so the Vue view can render them natively. The
entries themselves come from the shared icon-and-action registry via ``get_icons``,
so any registered host icon (HW/SW inventory, notes, custom actions, ...) shows up
automatically and stays permission-gated, exactly like in the legacy view.
"""

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.log import logger
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.painter.v0.helpers import replace_action_url_macros, transform_action_url
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import DynamicIcon, Row, StaticIcon
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.icon import IconConfig
from cmk.gui.views.icon.painter import get_icons, IconEntry, query_icon_row
from cmk.livestatus_client import MKLivestatusNotFoundError

from ._family import MONITOR_HOSTS_FAMILY

# "Edit host" (wato) and "Parameters" (rule_editor) are surfaced as explicit inline buttons.
_EXCLUDED_IDENTS = frozenset({"wato", "rule_editor"})


@api_model
class ActionMenuItem:
    icon_name: str = api_field(description="Icon to render for this action", example="inventory")
    title: str = api_field(
        description="Label shown for the action", example="Show HW/SW inventory tree"
    )
    url: str = api_field(
        description="URL the action links to",
        example="view.py?view_name=inv_host&host=web-server-01&site=local",
    )
    target: str | ApiOmitted = api_field(
        description="Target frame/window for the link (e.g. '_blank'). Omitted for same-frame links.",
        example="_blank",
        default_factory=ApiOmitted,
    )


@api_model
class HostActionMenuResponse:
    items: list[ActionMenuItem] = api_field(
        description="The action menu entries available for this host", example=[]
    )


def _icon_name(icon: StaticIcon | DynamicIcon) -> str:
    if isinstance(icon, StaticIcon):
        return str(icon.icon)
    if isinstance(icon, dict):
        return str(icon["icon"])
    return str(icon)


def _serialize_entry(entry: IconEntry, row: Row) -> ActionMenuItem | None:
    if entry.url_spec is None:
        return None

    url, target_frame = transform_action_url(entry.url_spec)
    url = replace_action_url_macros(url, "host", row)
    if url.startswith("onclick:"):
        # JavaScript command actions (e.g. reschedule) cannot be rendered as a native link.
        return None

    return ActionMenuItem(
        icon_name=_icon_name(entry.icon_name),
        title=entry.title or "",
        url=url,
        target=target_frame if target_frame else ApiOmitted(),
    )


def get_host_action_menu(
    hostname: Annotated[
        AnnotatedHostName,
        PathParam(description="The host name", example="web-server-01"),
    ],
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)],
        QueryParam(description="An existing site id", example="local"),
    ],
) -> HostActionMenuResponse:
    """List the action menu entries for a single host."""
    display_options.load_from_html(request, html)
    try:
        row = query_icon_row("host", hostname, site_id)
    except MKLivestatusNotFoundError:
        raise ProblemException(
            status=404,
            title="The requested host was not found",
            detail=f"The host {hostname!r} was not found on site {site_id!r}",
        ) from None

    entries = get_icons(
        "host",
        row,
        UserPermissions.from_config(active_config, permission_registry),
        IconConfig.from_config(active_config),
        toplevel=False,
        ignore_idents=_EXCLUDED_IDENTS,
    )

    items: list[ActionMenuItem] = []
    for entry in entries:
        # The dropdown only renders native links. Command icons (onclick JavaScript) and legacy
        # raw-HTML icons cannot be represented as one and are dropped; log them so a missing
        # action that still shows in the legacy view is diagnosable.
        if not isinstance(entry, IconEntry):
            logger.debug("action menu: dropping non-link icon entry for host %r", hostname)
            continue
        if (item := _serialize_entry(entry, row)) is None:
            logger.debug(
                "action menu: dropping command/link-less icon %r for host %r", entry.title, hostname
            )
            continue
        items.append(item)

    return HostActionMenuResponse(items=items)


ENDPOINT_GET_HOST_ACTION_MENU = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/{hostname}/action_menu",
        link_relation="cmk/host_action_menu",
        method="get",
    ),
    permissions=EndpointPermissions(
        # Declared for the permission tracker: the livestatus row query and get_icons already scope
        # visibility and gate each action per user, so no permission is required up front. This
        # mirrors the legacy action menu popup, which is accessible to normal users too.
        required=permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.OkayToIgnorePerm("general.see_all"),
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                ]
            )
        )
    ),
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=get_host_action_menu)},
)
