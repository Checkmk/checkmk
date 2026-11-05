#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The custom icons of a host or service row: the user's "Custom icons and actions" assigned by
rule, and the "Icon image" of the object.

They come from the legacy icon registry, so permissions and URL macros work as in the views.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.gui.config import active_config
from cmk.gui.dynamic_icon import resolve_icon_name
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.permissions import all_permissions
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view_utils import replace_action_url_macros, transform_action_url
from cmk.gui.views.icon.base import IconConfig
from cmk.gui.views.icon.entries import get_icons, IconEntry
from cmk.gui.views.icon.registry import all_icons
from cmk.livestatus_client import MultiSiteConnection
from cmk.livestatus_client.expressions import And, Or
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Hosts, Services
from cmk.shared_typing import icon as st
from cmk.web.utils.icons import DynamicIconName, StaticIcon

_ICON_IMAGE = "icon_image"


@dataclass(frozen=True)
class IconSource:
    """The livestatus values the custom icons of a host or service are made of."""

    actions: str
    """The ``ACTIONS`` custom variable: the comma separated ids of the assigned custom icons."""
    icon_image: str
    host_address: str
    """Needed for the ``$HOSTADDRESS$`` macro of action URLs."""


@api_model
class CustomIcon:
    ident: str = api_field(description="Identifier of the icon", example="my_wiki")
    title: str = api_field(description="Tooltip of the icon", example="Open the wiki page")
    icon_name: str = api_field(description="Name of the icon", example="wiki")
    icon_path: str | ApiOmitted = api_field(
        description="Path of an uploaded icon, omitted for a built-in one",
        example="images/icons/wiki.png",
        default_factory=ApiOmitted,
    )
    url: str | ApiOmitted = api_field(
        description="URL the icon links to, omitted for an icon without action",
        example="https://wiki.example.com/web-server-01",
        default_factory=ApiOmitted,
    )
    target: str | ApiOmitted = api_field(
        description="Target frame of the link, omitted for the current one",
        example="_blank",
        default_factory=ApiOmitted,
    )


def any_custom_icons(
    connection: MultiSiteConnection,
    what: Literal["host", "service"],
    *,
    host_name: str | None = None,
) -> bool:
    """Whether any host or service visible to the user has custom icons assigned; with a host
    name, only the services of that host count."""
    with_icons = Or(Services.custom_variable_names == "ACTIONS", Services.icon_image != "")
    query = (
        Query(
            [Hosts.name],
            Or(Hosts.custom_variable_names == "ACTIONS", Hosts.icon_image != ""),
            extra_headers=["Limit: 1"],
        )
        if what == "host"
        else Query(
            [Services.description],
            with_icons if host_name is None else And(with_icons, Services.host_name == host_name),
            extra_headers=["Limit: 1"],
        )
    )
    return query.first(connection) is not None


def custom_icons(
    what: Literal["host", "service"],
    *,
    site_id: str,
    host_name: str,
    service_name: str | None,
    source: IconSource,
) -> Sequence[CustomIcon]:
    """Icons without an action and the actions to show in the row; actions not shown in the row
    are left to the action menu."""
    row = _icon_row(what, site_id, host_name, service_name, source)
    wanted = {_ICON_IMAGE} | {
        ident for ident, icon in all_icons().items() if icon.type == "custom_icon"
    }
    entries = sorted(
        (
            (entry, toplevel)
            for toplevel in (True, False)
            for entry in get_icons(
                what,
                row,
                UserPermissions.from_config(active_config, all_permissions()),
                IconConfig.from_config(active_config),
                toplevel=toplevel,
                ignore_idents=all_icons().keys() - wanted,
            )
            if isinstance(entry, IconEntry)
        ),
        key=lambda pair: pair[0].sort_index,
    )
    return [
        icon
        for entry, toplevel in entries
        if (icon := _custom_icon(what, row, entry, toplevel)) is not None
    ]


def _icon_row(
    what: Literal["host", "service"],
    site_id: str,
    host_name: str,
    service_name: str | None,
    source: IconSource,
) -> Row:
    return {
        "site": site_id,
        "host_name": host_name,
        "host_address": source.host_address,
        "host_custom_variable_names": [],
        "host_custom_variable_values": [],
        "service_description": service_name,
        f"{what}_custom_variable_names": ["ACTIONS"],
        f"{what}_custom_variable_values": [source.actions],
        f"{what}_icon_image": source.icon_image,
    }


def _custom_icon(
    what: Literal["host", "service"], row: Row, entry: IconEntry, toplevel: bool
) -> CustomIcon | None:
    url, target = (None, None) if entry.url_spec is None else transform_action_url(entry.url_spec)
    if url is not None and (not toplevel or url.startswith("onclick:")):
        return None
    resolved = resolve_icon_name(
        (
            DynamicIconName(str(entry.icon_name.icon))
            if isinstance(entry.icon_name, StaticIcon)
            else entry.icon_name
        ),
        theme,
    )
    icon = resolved.icon if isinstance(resolved, st.EmblemIcon) else resolved
    return CustomIcon(
        ident=entry.ident or "",
        title=entry.title or "",
        icon_name=icon.id,
        icon_path=icon.path if isinstance(icon, st.UserIcon) else ApiOmitted(),
        url=ApiOmitted() if url is None else replace_action_url_macros(url, what, row),
        target=target or ApiOmitted(),
    )
