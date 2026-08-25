#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The icon and action entries of a host or service row.

Building the entries is independent of rendering them: the icon painters turn them
into HTML, while other consumers - the action menu, for instance - read them as data.
Keeping them apart lets a consumer take the entries without pulling in the painters.
"""

import contextlib
import traceback
from collections.abc import Container, Iterator
from dataclasses import dataclass
from typing import Literal

import cmk.ccc.regex
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import (
    ColumnName,
    DynamicIcon,
    IconNames,
    Row,
    StaticIcon,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client import livestatus_lql
from cmk.ruleset_matcher.tags import TagID
from cmk.utils.servicename import ServiceName
from cmk.web.utils.html import HTML

from .base import Icon, IconConfig
from .registry import all_icons

IconObjectType = Literal["host", "service"]


@dataclass
class ABCIconEntry:
    sort_index: int


@dataclass
class LegacyIconEntry(ABCIconEntry):
    code: HTML


@dataclass
class IconEntry(ABCIconEntry):
    icon_name: StaticIcon | DynamicIcon
    title: str | None = None
    url_spec: None | tuple[str, str] | str = None


def get_icons(
    what: IconObjectType,
    row: Row,
    user_permissions: UserPermissions,
    icon_config: IconConfig,
    *,
    toplevel: bool,
    ignore_idents: Container[str] = (),
) -> list[ABCIconEntry]:
    host_custom_vars = dict(
        zip(
            row["host_custom_variable_names"],
            row["host_custom_variable_values"],
        )
    )

    if what != "host":
        custom_vars = dict(
            zip(
                row[what + "_custom_variable_names"],
                row[what + "_custom_variable_values"],
            )
        )
    else:
        custom_vars = host_custom_vars

    # Extract needed custom variables
    tags = host_custom_vars.get("TAGS", "").split()
    user_icon_ids = custom_vars.get("ACTIONS", "").split(",")

    return sorted(
        _process_icons(
            what,
            row,
            tags,
            host_custom_vars,
            user_permissions,
            toplevel,
            user_icon_ids,
            icon_config,
            ignore_idents,
        ),
        key=lambda i: i.sort_index,
    )


def _process_icons(
    what: IconObjectType,
    row: Row,
    tags: list[TagID],
    custom_vars: dict[str, str],
    user_permissions: UserPermissions,
    toplevel: bool,
    user_icon_ids: list[str],
    icon_config: IconConfig,
    ignore_idents: Container[str] = (),
) -> list[ABCIconEntry]:
    icons: list[ABCIconEntry] = []
    for icon_id, icon in all_icons().items():
        if icon_id in ignore_idents:
            continue

        if icon.toplevel != toplevel:
            continue

        if icon.type == "custom_icon" and icon_id not in user_icon_ids:
            continue

        if not user.may("icons_and_actions.%s" % icon_id):
            continue

        try:
            for result in _process_icon(
                what, row, tags, custom_vars, user_permissions, icon_id, icon, icon_config
            ):
                icons.append(result)
        except Exception:
            icons.append(
                IconEntry(
                    sort_index=icon.sort_index,
                    icon_name=StaticIcon(IconNames.alert),
                    title=_("Exception in icon '%(icon_id)s': %(traceback)s")
                    % {
                        "icon_id": icon_id,
                        "traceback": traceback.format_exc(),
                    },
                )
            )
    return icons


def _process_icon(
    what: IconObjectType,
    row: Row,
    tags: list[TagID],
    custom_vars: dict[str, str],
    user_permissions: UserPermissions,
    icon_id: str,
    icon: Icon,
    icon_config: IconConfig,
) -> Iterator[ABCIconEntry]:
    # In old versions, the icons produced html code directly. The new API
    # is that the icon functions need to return:
    # a) None          - nothing to be rendered
    # b) single string - the icon name (without .png)
    # c) tuple         - icon, title
    # d) triple        - icon, title, url
    result = None
    try:
        result = icon.render(what, row, tags, custom_vars, user_permissions, icon_config)
    except Exception:
        if icon_config.debug:
            raise
        yield IconEntry(
            sort_index=icon.sort_index,
            icon_name=StaticIcon(IconNames.alert),
            title=_("Exception in icon '%(icon_id)s': %(traceback)s")
            % {"icon_id": icon_id, "traceback": traceback.format_exc()},
        )

    if result is None:
        return

    title: str | None = None
    url: None | tuple[str, str] | str = None
    icon_name: StaticIcon | DynamicIcon = StaticIcon(IconNames.trans)
    # DynamicIcon is an alias to str
    if isinstance(result, str | StaticIcon):
        icon_name = result
    elif isinstance(result, HTML):
        # TODO: This is handling the deprecated API with 1.2.7. Remove this one day. But there
        # are icons that still use this API. These need to be cleaned up before.
        # LM: There are icons that still use this API
        if str(result)[0] == "<":
            # seems like an old format icon (html code). In regular rendering
            # case (html), it can simply be appended to the output. Otherwise
            # extract the icon name from icon images
            if html.output_format == "html":
                yield LegacyIconEntry(sort_index=icon.sort_index, code=result)
            else:
                # Strip icon names out of HTML code that is generated by htmllib.render_icon()
                for n in cmk.ccc.regex.regex('<img src="([^"]*)"[^>]*>').findall(str(result)):
                    if n.startswith("images/"):
                        n = n[7:]
                    if n.startswith("icon_"):
                        n = n[5:]
                    if n.endswith(".png"):
                        n = n[:-4]
                    yield IconEntry(sort_index=icon.sort_index, icon_name=n)
            return
    elif len(result) == 2:
        icon_name, title = result  # type: ignore[assignment]
    elif len(result) == 3:
        icon_name, title, url = result  # type: ignore[assignment]
    else:
        raise NotImplementedError

    yield IconEntry(
        sort_index=icon.sort_index,
        icon_name=icon_name,
        title=title,
        url_spec=url,
    )


def iconpainter_columns(what: IconObjectType, toplevel: bool | None) -> list[ColumnName]:
    cols = {
        "site",
        "host_name",
        "host_address",
        "host_custom_variable_names",
        "host_custom_variable_values",
    }

    if what == "service":
        cols.update(
            [
                "service_description",
                "service_custom_variable_names",
                "service_custom_variable_values",
            ]
        )

    for icon in all_icons().values():
        if toplevel is None or toplevel == icon.toplevel:
            cols.update([what + "_" + c for c in icon.columns])
            cols.update(["host_" + c for c in icon.host_columns])
            if what == "service":
                cols.update(["service_" + c for c in icon.service_columns])

    return list(cols)


def query_icon_row(
    what: IconObjectType,
    host: HostName,
    site: SiteId,
    service_description: ServiceName | None = None,
) -> Row:
    """Fetch the livestatus row carrying all columns the action-menu icons need."""
    columns = list(iconpainter_columns(what, toplevel=False))
    with contextlib.suppress(ValueError):
        columns.remove("site")

    query = livestatus_lql([host], columns, service_description)
    with sites.prepend_site(), sites.only_sites(site):
        values = sites.live().query_row(query)

    return dict(zip(["site"] + columns, values))
