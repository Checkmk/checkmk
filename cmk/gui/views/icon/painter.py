#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.gui.htmllib.html import HTMLGenerator
from cmk.gui.i18n import _l
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter import Cell, InternalPainter, PainterConfig, PainterContext
from cmk.gui.type_defs import ColumnName, Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view_utils import (
    CellSpec,
    CSVExportError,
    replace_action_url_macros,
    transform_action_url,
)
from cmk.web.utils.html import HTML
from cmk.web.utils.icons import DynamicIcon, DynamicIconName, DynamicIconWithEmblem, StaticIcon

from .base import IconConfig
from .entries import (
    ABCIconEntry,
    get_icons,
    IconEntry,
    IconObjectType,
    iconpainter_columns,
    LegacyIconEntry,
)


def _icon_config(config: PainterConfig) -> IconConfig:
    return IconConfig(
        wato_enabled=config.wato_enabled,
        mkeventd_enabled=config.mkeventd_enabled,
        multisite_draw_ruleicon=config.multisite_draw_ruleicon,
        staleness_threshold=config.staleness_threshold,
        debug=config.debug,
    )


def _columns_service_icons() -> Sequence[ColumnName]:
    return iconpainter_columns("service", toplevel=None)


def _render_service_icons(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_icons(
        "service",
        row,
        _get_row_icons("service", row, context.user_permissions, _icon_config(context.config)),
    )


def _compute_data_service_icons(row: Row, context: PainterContext) -> list[DynamicIcon]:
    return [
        _handle_icon(i.icon_name)
        for i in _get_row_icons(
            "service", row, context.user_permissions, _icon_config(context.config)
        )
        if isinstance(i, IconEntry)
    ]


def _export_for_csv_service_icons(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    raise CSVExportError


def make_service_icons_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_icons",
        title=_l("Service icons"),
        short_title=_l("Icons"),
        columns=_columns_service_icons,
        groupable=False,
        printable=False,
        render=_render_service_icons,
        compute_data=_compute_data_service_icons,
        export_for_csv=_export_for_csv_service_icons,
    )


def _columns_host_icons() -> Sequence[ColumnName]:
    return iconpainter_columns("host", toplevel=None)


def _render_host_icons(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_icons(
        "host",
        row,
        _get_row_icons("host", row, context.user_permissions, _icon_config(context.config)),
    )


def _compute_data_host_icons(row: Row, context: PainterContext) -> list[DynamicIcon]:
    return [
        _handle_icon(i.icon_name)
        for i in _get_row_icons("host", row, context.user_permissions, _icon_config(context.config))
        if isinstance(i, IconEntry)
    ]


def _export_for_csv_host_icons(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    raise CSVExportError


def make_host_icons_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_icons",
        title=_l("Host icons"),
        short_title=_l("Icons"),
        columns=_columns_host_icons,
        groupable=False,
        printable=False,
        render=_render_host_icons,
        compute_data=_compute_data_host_icons,
        export_for_csv=_export_for_csv_host_icons,
    )


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

                output += HTMLGenerator.render_icon_button(
                    url, icon.title or "", icon.icon_name, onclick=onclick, target=target_frame
                )
            elif isinstance(icon.icon_name, StaticIcon):
                output += HTMLGenerator.render_static_icon(icon.icon_name, title=icon.title)
            else:
                output += HTMLGenerator.render_dynamic_icon(icon.icon_name, title=icon.title)
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
