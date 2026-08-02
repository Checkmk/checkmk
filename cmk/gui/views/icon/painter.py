#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter.v0 import Cell, Painter
from cmk.gui.type_defs import (
    ColumnName,
    DynamicIcon,
    DynamicIconName,
    DynamicIconWithEmblem,
    Row,
    StaticIcon,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view_utils import (
    CellSpec,
    CSVExportError,
    replace_action_url_macros,
    transform_action_url,
)

from .base import IconConfig
from .entries import (
    ABCIconEntry,
    get_icons,
    IconEntry,
    IconObjectType,
    iconpainter_columns,
    LegacyIconEntry,
)


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

    def _compute_data(self, row: Row, cell: Cell, user: LoggedInUser) -> list[DynamicIcon]:
        return [
            _handle_icon(i.icon_name)
            for i in _get_row_icons(
                "service", row, self._user_permissions, IconConfig.from_config(self.config)
            )
            if isinstance(i, IconEntry)
        ]

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError


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

    def _compute_data(self, row: Row, cell: Cell, user: LoggedInUser) -> list[DynamicIcon]:
        return [
            _handle_icon(i.icon_name)
            for i in _get_row_icons(
                "host", row, self._user_permissions, IconConfig.from_config(self.config)
            )
            if isinstance(i, IconEntry)
        ]

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError


def _handle_icon(icon: StaticIcon | DynamicIcon) -> DynamicIcon:
    if isinstance(icon, (str, dict)):
        # DynamicIcon
        return icon
    if isinstance(icon, StaticIcon):
        icon_name = DynamicIconName(str(icon.icon))
        if icon.emblem:
            return DynamicIconWithEmblem({"icon": icon_name, "emblem": icon.emblem})
        return icon_name
    raise RuntimeError(f"Can not handle icon: {icon}")


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
