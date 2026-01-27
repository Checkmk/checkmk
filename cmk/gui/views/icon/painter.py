#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import traceback
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal

import cmk.ccc.regex
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.painter.v0 import Cell, Painter
from cmk.gui.painter.v0.helpers import replace_action_url_macros, transform_action_url
from cmk.gui.type_defs import ColumnName, DynamicIcon, IconNames, Row, StaticIcon
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view_utils import CellSpec, CSVExportError
from cmk.utils.tags import TagID

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


class PainterServiceIcons(Painter):
    @property
    def ident(self) -> str:
        return "service_icons"

    def title(self, cell: Cell) -> str:
        return _("Service icons")

    def short_title(self, cell: Cell) -> str:
        return _("Icons")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return iconpainter_columns("service", toplevel=None)

    @property
    def printable(self) -> bool:
        return False

    def group_by(self, row: Row, cell: Cell) -> tuple[str]:
        return ("",)  # Do not account for in grouping

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_icons(
            "service",
            row,
            _get_row_icons(
                "service", row, self._user_permissions, IconConfig.from_config(self.config)
            ),
        )

    def _compute_data(
        self, row: Row, cell: Cell, user: LoggedInUser
    ) -> list[DynamicIcon | StaticIcon]:
        return [
            i.icon_name
            for i in _get_row_icons(
                "service", row, self._user_permissions, IconConfig.from_config(self.config)
            )
            if isinstance(i, IconEntry)
        ]

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError()


class PainterHostIcons(Painter):
    @property
    def ident(self) -> str:
        return "host_icons"

    def title(self, cell: Cell) -> str:
        return _("Host icons")

    def short_title(self, cell: Cell) -> str:
        return _("Icons")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return iconpainter_columns("host", toplevel=None)

    @property
    def printable(self) -> bool:
        return False

    def group_by(self, row: Row, cell: Cell) -> tuple[str]:
        return ("",)  # Do not account for in grouping

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_icons(
            "host",
            row,
            _get_row_icons(
                "host", row, self._user_permissions, IconConfig.from_config(self.config)
            ),
        )

    def _compute_data(
        self, row: Row, cell: Cell, user: LoggedInUser
    ) -> list[StaticIcon | DynamicIcon]:
        return [
            i.icon_name
            for i in _get_row_icons(
                "host", row, self._user_permissions, IconConfig.from_config(self.config)
            )
            if isinstance(i, IconEntry)
        ]

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError()


def _paint_icons(
    what: IconObjectType, row: Row, toplevel_icons: Sequence[ABCIconEntry]
) -> CellSpec:
    """Paint column with various icons

    The icons use a plug-in based mechanism so it is possible to register own icon "handlers".
    """
    output = HTML.empty()
    for icon in toplevel_icons:
        if isinstance(icon, IconEntry):
            if icon.url_spec:
                url, target_frame = transform_action_url(icon.url_spec)
                url = replace_action_url_macros(url, what, row)

                onclick = ""
                if url.startswith("onclick:"):
                    onclick = url[8:]
                    url = "javascript:void(0)"

                output += html.render_icon_button(
                    url, icon.title or "", icon.icon_name, onclick=onclick, target=target_frame
                )
            elif isinstance(icon.icon_name, StaticIcon):
                output += html.render_static_icon(icon.icon_name, title=icon.title)
            else:
                output += html.render_dynamic_icon(icon.icon_name, title=icon.title)
        elif isinstance(icon, LegacyIconEntry):
            output += icon.code

    return "icons", output


def _get_row_icons(
    what: IconObjectType, row: Row, user_permissions: UserPermissions, icon_config: IconConfig
) -> list[ABCIconEntry]:
    # EC: In case of unrelated events also skip rendering this painter. All the icons
    # that display a host state are useless in this case. Maybe we make this decision
    # individually for the single icons one day.
    if not row["host_name"] or row.get("event_is_unrelated"):
        return []  # Host probably does not exist

    return get_icons(what, row, user_permissions, icon_config, toplevel=True)


def get_icons(
    what: IconObjectType,
    row: Row,
    user_permissions: UserPermissions,
    icon_config: IconConfig,
    *,
    toplevel: bool,
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
) -> list[ABCIconEntry]:
    icons: list[ABCIconEntry] = []
    for icon_id, icon in all_icons().items():
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
                    title=_("Exception in icon '%s': %s")
                    % (
                        icon_id,
                        traceback.format_exc(),
                    ),
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
            title=_("Exception in icon '%s': %s") % (icon_id, traceback.format_exc()),
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
        icon_name, title = result  # type: ignore[misc]
    elif len(result) == 3:
        icon_name, title, url = result  # type: ignore[misc]
    else:
        raise NotImplementedError()

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
