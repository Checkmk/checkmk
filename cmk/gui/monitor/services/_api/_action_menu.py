#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Per-service action menu for the host services monitoring view.

The service counterpart of the hosts view's action menu: it exposes the legacy
"service icons" (the entries behind the three-dots button in a view row) as typed JSON,
read from the same icon-and-action registry via ``get_icons``, so every registered
service icon (logwatch, graphs, custom actions, ...) shows up automatically and stays
permission-gated exactly as in the legacy view.

The models carry a "Service" prefix because the OpenAPI spec registers component schemas
by class name across every endpoint family, where the hosts action menu already owns the
unprefixed names.
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
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import DynamicIcon, Row, StaticIcon
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view_utils import replace_action_url_macros, transform_action_url
from cmk.gui.views.icon.base import IconConfig
from cmk.gui.views.icon.entries import get_icons, IconEntry, query_icon_row
from cmk.livestatus_client import MKLivestatusNotFoundError
from cmk.utils.servicename import ServiceName
from cmk.web.utils import permission_verification as permissions

from ._family import MONITOR_SERVICES_FAMILY

# "Parameters" (rule_editor) is surfaced as an explicit inline button of the slide-in header.
_EXCLUDED_IDENTS = frozenset({"rule_editor"})


@api_model
class ServiceActionMenuItem:
    icon_name: str = api_field(description="Icon to render for this action", example="logwatch")
    title: str = api_field(description="Label shown for the action", example="Open log file viewer")
    url: str = api_field(
        description="URL the action links to",
        example="view.py?view_name=logwatch&host=web-server-01&site=local",
    )
    target: str | ApiOmitted = api_field(
        description="Target frame/window for the link (e.g. '_blank'). Omitted for same-frame links.",
        example="_blank",
        default_factory=ApiOmitted,
    )


@api_model
class ServiceActionMenuResponse:
    items: list[ServiceActionMenuItem] = api_field(
        description="The action menu entries available for this service", example=[]
    )


def _icon_name(icon: StaticIcon | DynamicIcon) -> str:
    if isinstance(icon, StaticIcon):
        return str(icon.icon)
    if isinstance(icon, dict):
        return str(icon["icon"])
    return str(icon)


def _serialize_entry(entry: IconEntry, row: Row) -> ServiceActionMenuItem | None:
    if entry.url_spec is None:
        return None

    url, target_frame = transform_action_url(entry.url_spec)
    url = replace_action_url_macros(url, "service", row)
    if url.startswith("onclick:"):
        # JavaScript command actions (e.g. reschedule) cannot be rendered as a native link.
        return None

    return ServiceActionMenuItem(
        icon_name=_icon_name(entry.icon_name),
        title=entry.title or "",
        url=url,
        target=target_frame if target_frame else ApiOmitted(),
    )


def get_service_action_menu(
    hostname: Annotated[
        AnnotatedHostName,
        PathParam(description="Host name", example="web-server-01"),
    ],
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)],
        QueryParam(description="An existing site id", example="local"),
    ],
    service_name: Annotated[
        str,
        QueryParam(description="The service name", example="CPU utilization"),
    ],
) -> ServiceActionMenuResponse:
    """List the action menu entries for a single service of a host."""
    display_options.load_from_html(request, html)
    try:
        row = query_icon_row("service", hostname, site_id, ServiceName(service_name))
    except MKLivestatusNotFoundError:
        raise ProblemException(
            status=404,
            title="The requested service was not found",
            detail=(
                f"The service {service_name!r} of host {hostname!r} was not found on site "
                f"{site_id!r}"
            ),
        ) from None

    entries = get_icons(
        "service",
        row,
        UserPermissions.from_config(active_config, permission_registry),
        IconConfig.from_config(active_config),
        toplevel=False,
        ignore_idents=_EXCLUDED_IDENTS,
    )

    items: list[ServiceActionMenuItem] = []
    for entry in entries:
        # The dropdown only renders native links. Command icons (onclick JavaScript) and legacy
        # raw-HTML icons cannot be represented as one and are dropped; log them so a missing
        # action that still shows in the legacy view is diagnosable.
        if not isinstance(entry, IconEntry):
            logger.debug(
                "action menu: dropping non-link icon entry for service %(service_name)r of host"
                " %(hostname)r",
                {"service_name": service_name, "hostname": hostname},
            )
            continue
        if (item := _serialize_entry(entry, row)) is None:
            logger.debug(
                "action menu: dropping command/link-less icon %(entry_title)r for service"
                " %(service_name)r of host %(hostname)r",
                {"entry_title": entry.title, "service_name": service_name, "hostname": hostname},
            )
            continue
        items.append(item)

    return ServiceActionMenuResponse(items=items)


ENDPOINT_GET_SERVICE_ACTION_MENU = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/{hostname}/service/action_menu",
        link_relation="cmk/service_action_menu",
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
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=get_service_action_menu)},
)
