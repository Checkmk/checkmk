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

A page may also ask for the links into Setup on the service, which the legacy menu lacks: they are
checked the way Setup checks them, which costs reading Setup's folders, so only a page that offers
them nowhere else asks.

The models carry a "Service" prefix because the OpenAPI spec registers component schemas
by class name across every endpoint family, where the hosts action menu already owns the
unprefixed names.
"""

from http import HTTPStatus
from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.htmllib.generator import ClickAction
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.log import logger
from cmk.gui.monitor.command import service_setup_links, SetupLink
from cmk.gui.monitor.setup_folders import SetupFolderSource
from cmk.gui.monitor.shared import may_open_in_setup, resolved_icon
from cmk.gui.openapi.framework import (
    ApiConfig,
    ApiContext,
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
from cmk.gui.permissions import all_permissions
from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view_utils import replace_action_url_macros, transform_action_url
from cmk.gui.views.icon.base import IconConfig
from cmk.gui.views.icon.entries import get_icons, IconEntry, query_icon_row
from cmk.livestatus_client import MKLivestatusNotFoundError
from cmk.shared_typing import icon as st
from cmk.utils.servicename import ServiceName
from cmk.web.utils import permission_verification as permissions
from cmk.web.utils.icons import DynamicIcon, StaticIcon

from .._models import CheckType
from ._family import MONITOR_SERVICES_FAMILY

# Shared by the table row and the slide-in, so only what both offer on their own is left out:
# "Parameters" (rule_editor) is a row action, a slide-in header button, or one of the Setup links
# below, which ask what Setup asks before it opens the page.
_EXCLUDED_IDENTS = frozenset({"rule_editor"})

# Read for the Setup links whichever icons the menu shows, as the configuration decides that.
_SETUP_LINK_COLUMNS = ("host_filename", "service_check_type")


@api_model
class ServiceActionMenuItem:
    ident: str | ApiOmitted = api_field(
        description="Identifier of the icon providing this action",
        example="logwatch",
        default_factory=ApiOmitted,
    )
    icon_name: str = api_field(description="Icon to render for this action", example="logwatch")
    icon_path: str | ApiOmitted = api_field(
        description="Path of an uploaded icon, omitted for a built-in one",
        example="images/icons/wiki.png",
        default_factory=ApiOmitted,
    )
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
    if entry.url_spec is None or isinstance(entry.url_spec, ClickAction):
        # Click actions (e.g. reschedule) cannot be rendered as a native link.
        return None

    url, target_frame = transform_action_url(entry.url_spec)
    url = replace_action_url_macros(url, "service", row)

    icon = resolved_icon(entry.icon_name)
    return ServiceActionMenuItem(
        ident=entry.ident if entry.ident else ApiOmitted(),
        icon_name=_icon_name(entry.icon_name),
        icon_path=icon.path if isinstance(icon, st.UserIcon) else ApiOmitted(),
        title=entry.title or "",
        url=url,
        target=target_frame if target_frame else ApiOmitted(),
    )


def _setup_link_item(link: SetupLink, hostname: str, service_name: str) -> ServiceActionMenuItem:
    return ServiceActionMenuItem(
        ident=link.ident,
        icon_name=link.icon,
        title=link.title,
        url=link.url_for(host=hostname, service=service_name),
    )


def _offers_setup_links(row: Row, config: ApiConfig) -> bool:
    """Whether the service of ``row`` gets links into Setup at all, whoever asks.

    The parameters stand in for the legacy rule editor icon, so they follow its rules: a shadow
    service has no parameters, and the admin may hide the link from every service.
    """
    return row["service_check_type"] != CheckType.SHADOW and config.multisite_draw_ruleicon


def _icon_items(row: Row, hostname: str, service_name: str) -> list[ServiceActionMenuItem]:
    """The entries the registered service icons offer, as the legacy action menu shows them."""
    entries = get_icons(
        "service",
        row,
        UserPermissions.from_config(active_config, all_permissions()),
        IconConfig.from_config(active_config),
        toplevel=False,
        ignore_idents=_EXCLUDED_IDENTS,
    )

    items: list[ServiceActionMenuItem] = []
    for entry in entries:
        # The dropdown only renders native links. Command icons (click actions) and legacy
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

    return items


def make_endpoint_get_service_action_menu(setup_folders: SetupFolderSource) -> VersionedEndpoint:
    """The endpoint listing the actions on one service, asking `setup_folders` who may open its
    host in Setup."""

    def get_service_action_menu(
        hostname: Annotated[
            AnnotatedHostName,
            PathParam(description="Host name", example="web-server-01"),
        ],
        site_id: Annotated[
            Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_be_authorized)],
            QueryParam(description="An existing site id", example="local"),
        ],
        service_name: Annotated[
            str,
            QueryParam(description="The service name", example="CPU utilization"),
        ],
        api_context: ApiContext,
        include_setup_links: Annotated[
            bool,
            QueryParam(
                description=(
                    "Also list the links into Setup on the service the user may follow, such as "
                    "its parameters. Asking Setup costs reading its folders, so only ask where "
                    "the page offers these links nowhere else."
                ),
                example="true",
            ),
        ] = False,
    ) -> ServiceActionMenuResponse:
        """List the action menu entries for a single service of a host."""
        display_options.load_from_html(request, html)
        try:
            row = query_icon_row(
                "service",
                hostname,
                site_id,
                ServiceName(service_name),
                extra_columns=_SETUP_LINK_COLUMNS if include_setup_links else (),
            )
        except MKLivestatusNotFoundError:
            raise ProblemException(
                status=HTTPStatus.NOT_FOUND,
                title="The requested service was not found",
                detail=(
                    f"The service {service_name!r} of host {hostname!r} was not found on site "
                    f"{site_id!r}"
                ),
            ) from None

        setup_links = (
            service_setup_links(api_context.config, api_context.user)
            if include_setup_links and _offers_setup_links(row, api_context.config)
            else []
        )
        # Setup restricts a host to the contact groups its permissions name, so it may refuse a
        # user the host even where they may see its parameters. Setup is asked about the folder
        # the host's file is in alone.
        if setup_links and not may_open_in_setup(
            setup_folders(api_context.config, api_context.user).may_read_host,
            hostname,
            row["host_filename"],
        ):
            setup_links = []

        # The Setup links lead the menu: a row puts the commands it runs itself, such as
        # rescheduling, ahead of the menu, so they follow those right away.
        return ServiceActionMenuResponse(
            items=[
                *(_setup_link_item(link, hostname, service_name) for link in setup_links),
                *_icon_items(row, hostname, service_name),
            ]
        )

    return VersionedEndpoint(
        metadata=EndpointMetadata(
            path="/monitor/hosts/{hostname}/service/action_menu",
            link_relation="cmk/service_action_menu",
            method="get",
        ),
        permissions=EndpointPermissions(
            # Declared for the permission tracker: the livestatus row query scopes visibility and
            # get_icons gates each action per user, so no permission is required up front. This
            # mirrors the legacy action menu popup, which is accessible to normal users too. Which
            # permissions are checked depends on the icons registered in the edition, and on
            # whether the Setup links were asked for.
            required=permissions.Undocumented(
                permissions.DynamicRuntimePerm(
                    description="Visibility of each action is gated per user at runtime.",
                )
            )
        ),
        doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
        behavior=EndpointBehavior(skip_locking=True),
        versions={APIVersion.INTERNAL: EndpointHandler(handler=get_service_action_menu)},
    )
