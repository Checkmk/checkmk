#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for internals and the plugins"""

# TODO: More feature related splitting up would be better

from __future__ import annotations

import abc
import os
import re
import time
import traceback
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from html import unescape
from pathlib import Path
from typing import Any, Literal, Union

import livestatus
from livestatus import SiteId

import cmk.utils.plugin_registry
import cmk.utils.regex
import cmk.utils.render
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.type_defs import HostName, LabelSources, ServiceName, TaggroupIDToTagID, TimeRange

import cmk.gui.painters.v1.painters
import cmk.gui.sites as sites
import cmk.gui.utils
import cmk.gui.utils.escaping as escaping
import cmk.gui.view_utils
import cmk.gui.visuals as visuals
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, ungettext
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.num_split import cmp_num_split as _cmp_num_split
from cmk.gui.painters.v1.helpers import (  # noqa: F401 # pylint: disable=unused-import
    get_perfdata_nth_value,
    is_stale,
    paint_stalified,
)
from cmk.gui.painters.v1.painter_lib import experimental_painter_registry
from cmk.gui.painters.v1.painter_lib import Painter as V1Painter
from cmk.gui.painters.v1.painter_lib import PainterConfiguration
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.plugins.metrics.utils import CombinedGraphMetricSpec
from cmk.gui.sorter import register_sorter, sorter_registry
from cmk.gui.type_defs import (
    ColumnName,
    CombinedGraphSpec,
    HTTPVariables,
    LivestatusQuery,
    PainterName,
    PainterParameters,
    PainterSpec,
    Row,
    Rows,
    SorterFunction,
    SorterName,
    SorterSpec,
    ViewName,
    ViewSpec,
    VisualLinkSpec,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.theme import theme
from cmk.gui.utils.urls import makeuri, urlencode
from cmk.gui.valuespec import ValueSpec
from cmk.gui.view_utils import CellSpec, get_host_list_links

ExportCellContent = str | dict[str, Any]
PDFCellContent = Union[str | tuple[Literal["icon"], str]]
PDFCellSpec = tuple[str, PDFCellContent]
CommandSpecWithoutSite = str
CommandSpecWithSite = tuple[str | None, CommandSpecWithoutSite]
CommandSpec = CommandSpecWithoutSite | CommandSpecWithSite
CommandActionResult = Union[tuple[CommandSpecWithoutSite | Sequence[CommandSpec], str], None]
CommandExecutor = Callable[[CommandSpec, SiteId | None], None]
InventoryHintSpec = dict[str, Any]


def group_value(row: Row, group_cells: Sequence[Cell]) -> Hashable:
    """The Group-value of a row is used for deciding whether
    two rows are in the same group or not"""
    group = []
    for cell in group_cells:
        painter = cell.painter()

        group_by_val = painter.group_by(row, cell)
        if group_by_val is not None:
            group.append(group_by_val)

        else:
            for c in painter.columns:
                if c in row:
                    group.append(row[c])

    return _create_dict_key(group)


def _create_dict_key(value: Any) -> Hashable:
    if isinstance(value, (list, tuple)):
        return tuple(map(_create_dict_key, value))
    if isinstance(value, dict):
        return tuple((k, _create_dict_key(v)) for (k, v) in sorted(value.items()))
    return value


class Layout(abc.ABC):
    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a layout. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """Short human readable title of the layout"""
        raise NotImplementedError()

    @abc.abstractmethod
    def render(
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        """Render the given data in this layout"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def can_display_checkboxes(self) -> bool:
        """Whether this layout can display checkboxes for selecting rows"""
        raise NotImplementedError()

    @property
    def painter_options(self) -> list[str]:
        """Returns the painter option identities used by this layout"""
        return []

    @property
    def has_individual_csv_export(self) -> bool:
        """Whether this layout has an individual CSV export implementation"""
        return False

    def csv_export(
        self, rows: Rows, view: ViewSpec, group_cells: Sequence[Cell], cells: Sequence[Cell]
    ) -> None:
        """Render the given data using this layout for CSV"""


class ViewLayoutRegistry(cmk.utils.plugin_registry.Registry[type[Layout]]):
    def plugin_name(self, instance: type[Layout]) -> str:
        return instance().ident

    def get_choices(self) -> list[tuple[str, str]]:
        choices = []
        for plugin_class in self.values():
            layout = plugin_class()
            choices.append((layout.ident, layout.title))

        return choices


layout_registry = ViewLayoutRegistry()


class CommandGroup(abc.ABC):
    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a command group. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def sort_index(self) -> int:
        raise NotImplementedError()


class CommandGroupRegistry(cmk.utils.plugin_registry.Registry[type[CommandGroup]]):
    def plugin_name(self, instance: type[CommandGroup]) -> str:
        return instance().ident


command_group_registry = CommandGroupRegistry()


# TODO: Kept for pre 1.6 compatibility
def register_command_group(ident: str, title: str, sort_index: int) -> None:
    cls = type(
        "LegacyCommandGroup%s" % ident.title(),
        (CommandGroup,),
        {
            "_ident": ident,
            "_title": title,
            "_sort_index": sort_index,
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._title),
            "sort_index": property(lambda s: s._sort_index),
        },
    )
    command_group_registry.register(cls)


class Command(abc.ABC):
    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a command. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def permission(self) -> Permission:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def tables(self) -> list[str]:
        """List of livestatus table identities the action may be used with"""
        raise NotImplementedError()

    def user_dialog_suffix(
        self, title: str, len_action_rows: int, cmdtag: Literal["HOST", "SVC"]
    ) -> str:
        return title + " the following %(count)d %(what)s?" % {
            "count": len_action_rows,
            "what": ungettext(
                "host",
                "hosts",
                len_action_rows,
            )
            if cmdtag == "HOST"
            else ungettext(
                "service",
                "services",
                len_action_rows,
            ),
        }

    def user_confirm_options(
        self, len_rows: int, cmdtag: Literal["HOST", "SVC"]
    ) -> list[tuple[str, str]]:
        return [(_("Confirm"), "_do_confirm")]

    def render(self, what: str) -> None:
        raise NotImplementedError()

    def action(
        self, cmdtag: Literal["HOST", "SVC"], spec: str, row: Row, row_index: int, action_rows: Rows
    ) -> CommandActionResult:
        result = self._action(cmdtag, spec, row, row_index, action_rows)
        if result:
            commands, title = result
            return commands, self.user_dialog_suffix(title, len(action_rows), cmdtag)
        return None

    @abc.abstractmethod
    def _action(
        self, cmdtag: Literal["HOST", "SVC"], spec: str, row: Row, row_index: int, action_rows: Rows
    ) -> CommandActionResult:
        raise NotImplementedError()

    @property
    def group(self) -> type[CommandGroup]:
        """The command group the commmand belongs to"""
        return command_group_registry["various"]

    @property
    def only_view(self) -> str | None:
        """View name to show a view exclusive command for"""
        return None

    @property
    def icon_name(self) -> str:
        return "commands"

    @property
    def is_show_more(self) -> bool:
        return False

    @property
    def is_shortcut(self) -> bool:
        return False

    @property
    def is_suggested(self) -> bool:
        return False

    def executor(self, command: CommandSpec, site: SiteId | None) -> None:
        """Function that is called to execute this action"""
        # We only get CommandSpecWithoutSite here. Can be cleaned up once we have a dedicated
        # object type for the command
        assert isinstance(command, str)
        sites.live().command("[%d] %s" % (int(time.time()), command), site)


class CommandRegistry(cmk.utils.plugin_registry.Registry[type[Command]]):
    def plugin_name(self, instance: type[Command]) -> str:
        return instance().ident


command_registry = CommandRegistry()


# TODO: Kept for pre 1.6 compatibility
def register_legacy_command(spec: dict[str, Any]) -> None:
    ident = re.sub("[^a-zA-Z]", "", spec["title"]).lower()
    cls = type(
        "LegacyCommand%s" % str(ident).title(),
        (Command,),
        {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._spec["title"]),
            "permission": property(lambda s: permission_registry[s._spec["permission"]]),
            "tables": property(lambda s: s._spec["tables"]),
            "render": lambda s: s._spec["render"](),
            "action": lambda s, cmdtag, spec, row, row_index, num_rows: s._spec["action"](
                cmdtag, spec, row
            ),
            "_action": lambda s, cmdtag, spec, row, row_index, num_rows: s._spec["_action"](
                cmdtag, spec, row
            ),
            "group": lambda s: command_group_registry[s._spec.get("group", "various")],
            "only_view": lambda s: s._spec.get("only_view"),
        },
    )
    command_registry.register(cls)


class CSVExportError(Exception):
    pass


class JSONExportError(Exception):
    pass


# TODO: Return value of render() could be cleaned up e.g. to a named tuple with an
# optional CSS class. A lot of painters don't specify CSS classes.
# TODO: Since we have the reporting also working with the painters it could be useful
# to make the render function return structured data which can then be rendered for
# HTML and PDF.
# TODO: A lot of painter classes simply display plain livestatus column values. These
# could be replaced with some simpler generic definition.
class Painter(abc.ABC):
    """A painter computes HTML code based on information from a data row and
    creates a CSS class for one display column.

    Please note, that there is no
    1:1 relation between data columns and display columns. A painter can
    make use of more than one data columns. One example is the current
    service state. It uses the columns "service_state" and "has_been_checked".
    """

    @staticmethod
    def uuid_col(cell: Cell) -> str:
        # This method is only overwritten in two subclasses and does not even
        # use `self`.  This is all very fishy.
        return ""

    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a painter. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractmethod
    def title(self, cell: "Cell") -> str:
        """Used as display string for the painter in the GUI (e.g. views using this painter)"""
        raise NotImplementedError()

    def title_classes(self) -> list[str]:
        """Additional css classes used to render the title"""
        return []

    @property
    @abc.abstractmethod
    def columns(self) -> Sequence[ColumnName]:
        """Livestatus columns needed for this painter"""
        raise NotImplementedError()

    def dynamic_columns(self, cell: "Cell") -> list[ColumnName]:
        """Return list of dynamically generated column as specified by Cell

        Some columns for the Livestatus query need to be generated at
        execution time, knowing user configuration. Using the Cell object
        generated the required column names."""
        return []

    def derive(self, rows: Rows, cell: "Cell", dynamic_columns: list[ColumnName] | None) -> None:
        """Post process query according to cell

        This function processes data immediately after it is handled back
        from the Livestatus Datasource. It gets access to the entire
        returned table and sequentially to each of the cells configured.

        rows: List of Dictionaries
             Data table of the returning query. Every element is a
             dictionary which keys are the column names. Derive function
             should mutate in place each row. When processing data or
             generating new columns.
        cell: Cell
            Used to retrieve configuration parameters
        dynamic_columns: list[str]
            The exact dynamic columns generated by the painter before the
            query. As they might be required to find them again within the
            data."""

    def short_title(self, cell: "Cell") -> str:
        """Used as display string for the painter e.g. as table header
        Falls back to the full title if no short title is given"""
        return self.title(cell)

    def export_title(self, cell: "Cell") -> str:
        """Used for exporting views in JSON/CSV/python format"""
        return self.ident

    def list_title(self, cell: "Cell") -> str:
        """Override this to define a custom title for the painter in the view editor
        Falls back to the full title if no short title is given"""
        return self.title(cell)

    def group_by(
        self,
        row: Row,
        cell: "Cell",
    ) -> None | str | tuple[str, ...] | tuple[tuple[str, str], ...]:
        """When a value is returned, this is used instead of the value produced by self.paint()"""
        return None

    @property
    def parameters(self) -> ValueSpec | None:
        """Returns either the valuespec of the painter parameters or None"""
        return None

    @property
    def painter_options(self) -> list[str]:
        """Returns a list of painter option names that affect this painter"""
        return []

    @property
    def printable(self) -> bool | str:
        """
        True       : Is printable in PDF
        False      : Is not printable at all
        "<string>" : ID of a painter_printer (Reporting module)
        """
        return True

    @property
    def use_painter_link(self) -> bool:
        """Allow the view spec to define a view / dashboard to link to"""
        return True

    @property
    def sorter(self) -> SorterName | None:
        """Returns the optional name of the sorter for this painter"""
        return None

    # TODO: Cleanup this hack
    @property
    def load_inv(self) -> bool:
        """Whether or not to load the HW/SW inventory for this column"""
        return False

    # TODO At the moment we use render as fallback but in the future every
    # painter should implement explicit
    #   - _compute_data
    #   - render
    #   - export methods
    # As soon as this is done all four methods will be abstract.

    # See first implementations: PainterInventoryTree, PainterHostLabels, ...

    # TODO For PDF or Python output format we implement additional methods.

    def _compute_data(self, row: Row, cell: "Cell") -> object:
        return self.render(row, cell)[1]

    @abc.abstractmethod
    def render(self, row: Row, cell: "Cell") -> CellSpec:
        """Renders the painter for the given row
        The paint function gets one argument: A data row, which is a python
        dictionary representing one data object (host, service, ...). Its
        keys are the column names, its values the actual values from livestatus
        (typed: numbers are float or int, not string)

        The paint function must return a pair of two strings:
            - A CSS class for the TD of the column and
            - a Text string or HTML code for painting the column

        That class is optional and set to "" in most cases. Currently CSS
        styles are not modular and all defined in check_mk.css. This will
        change in future."""
        raise NotImplementedError()

    def export_for_csv(self, row: Row, cell: "Cell") -> str | HTML:
        """Render the content of the painter for CSV export based on the given row.

        If the data of a painter can not be exported as CSV (like trees), then this method
        raises a 'CSVExportError'.
        """
        if isinstance(data := self._compute_data(row, cell), (str, HTML)):
            return data
        raise ValueError("Data must be of type 'str' or 'HTML' but is %r" % type(data))

    def export_for_json(self, row: Row, cell: "Cell") -> object:
        """Render the content of the painter for JSON export based on the given row.

        If the data of a painter can not be exported as JSON, then this method
        raises a 'JSONExportError'.
        """
        return self._compute_data(row, cell)


class Painter2(Painter):
    # Poor man's composition:  Renderer differs between CRE and non-CRE.
    resolve_combined_single_metric_spec: Callable[
        [CombinedGraphSpec], Sequence[CombinedGraphMetricSpec]
    ] | None = None


class PainterRegistry(cmk.utils.plugin_registry.Registry[type[Painter]]):
    def plugin_name(self, instance: type[Painter]) -> str:
        return instance().ident


painter_registry = PainterRegistry()


# Kept for pre 1.6 compatibility. But also the inventory.py uses this to
# register some painters dynamically
def register_painter(ident: str, spec: dict[str, Any]) -> None:
    paint_function = spec["paint"]
    cls = type(
        "LegacyPainter%s" % ident.title(),
        (Painter,),
        {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": lambda s, cell: s._spec["title"],
            "short_title": lambda s, cell: s._spec.get("short", s.title),
            "columns": property(lambda s: s._spec["columns"]),
            "render": lambda self, row, cell: paint_function(row),
            "export_for_csv": (
                lambda self, row, cell: spec["export_for_csv"](row, cell)
                if "export_for_csv" in spec
                else paint_function(row)[1]
            ),
            "export_for_json": (
                lambda self, row, cell: spec["export_for_json"](row, cell)
                if "export_for_json" in spec
                else paint_function(row)[1]
            ),
            "group_by": lambda self, row, cell: self._spec.get("groupby"),
            "parameters": property(lambda s: s._spec.get("params")),
            "painter_options": property(lambda s: s._spec.get("options", [])),
            "printable": property(lambda s: s._spec.get("printable", True)),
            "sorter": property(lambda s: s._spec.get("sorter", None)),
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),
        },
    )
    painter_registry.register(cls)


# TODO: Refactor to plugin_registries
view_hooks: dict = {}
inventory_displayhints: dict[str, InventoryHintSpec] = {}
# For each view a function can be registered that has to return either True
# or False to show a view as context link
view_is_enabled: dict = {}


def transform_action_url(url_spec: tuple[str, str] | str) -> tuple[str, str | None]:
    if isinstance(url_spec, tuple):
        return url_spec
    return (url_spec, None)


def paint_host_list(site: SiteId, hosts: list[HostName]) -> CellSpec:
    return "", HTML(
        ", ".join(
            get_host_list_links(
                site,
                [str(host) for host in hosts],
            )
        )
    )


def format_plugin_output(output: str, row: Row) -> HTML:
    return cmk.gui.view_utils.format_plugin_output(
        output, row, shall_escape=active_config.escape_plugin_output
    )


def get_tag_groups(row: Row, what: str) -> TaggroupIDToTagID:
    # Sites with old versions that don't have the tag groups column return
    # None for this field. Convert this to the default value
    groups = row.get("%s_tags" % what, {}) or {}
    assert isinstance(groups, dict)
    return groups


def get_label_sources(row: Row, what: str) -> LabelSources:
    # Sites with old versions that don't have the label_sources column return
    # None for this field. Convert this to the default value
    sources = row.get("%s_label_sources" % what, {}) or {}
    assert isinstance(sources, dict)
    return sources


def paint_nagiosflag(row: Row, field: ColumnName, bold_if_nonzero: bool) -> CellSpec:
    nonzero = row[field] != 0
    return (
        "badflag" if nonzero == bold_if_nonzero else "goodflag",
        HTMLWriter.render_span(_("yes") if nonzero else _("no")),
    )


def declare_1to1_sorter(
    painter_name: PainterName, func: SorterFunction, col_num: int = 0, reverse: bool = False
) -> PainterName:
    painter = painter_registry[painter_name]()

    register_sorter(
        painter_name,
        {
            "title": painter.title,
            "columns": painter.columns,
            "cmp": (lambda self, r1, r2: func(painter.columns[col_num], r2, r1))
            if reverse
            else lambda self, r1, r2: func(painter.columns[col_num], r1, r2),
        },
    )
    return painter_name


def cmp_simple_number(column: ColumnName, r1: Row, r2: Row) -> int:
    v1 = r1[column]
    v2 = r2[column]
    return (v1 > v2) - (v1 < v2)


def cmp_num_split(column: ColumnName, r1: Row, r2: Row) -> int:
    return _cmp_num_split(r1[column].lower(), r2[column].lower())


def cmp_simple_string(column: ColumnName, r1: Row, r2: Row) -> int:
    v1, v2 = r1.get(column, ""), r2.get(column, "")
    return cmp_insensitive_string(v1, v2)


def cmp_insensitive_string(v1: str, v2: str) -> int:
    c = (v1.lower() > v2.lower()) - (v1.lower() < v2.lower())
    # force a strict order in case of equal spelling but different
    # case!
    if c == 0:
        return (v1 > v2) - (v1 < v2)
    return c


def cmp_string_list(column: ColumnName, r1: Row, r2: Row) -> int:
    v1 = "".join(r1.get(column, []))
    v2 = "".join(r2.get(column, []))
    return cmp_insensitive_string(v1, v2)


def cmp_service_name_equiv(r: str) -> int:
    if r == "Check_MK":
        return -6
    if r == "Check_MK Agent":
        return -5
    if r == "Check_MK Discovery":
        return -4
    if r == "Check_MK inventory":
        return -3  # FIXME: Remove old name one day
    if r == "Check_MK HW/SW Inventory":
        return -2
    return 0


def cmp_custom_variable(r1: Row, r2: Row, key: str, cmp_func: SorterFunction) -> int:
    return (get_custom_var(r1, key) > get_custom_var(r2, key)) - (
        get_custom_var(r1, key) < get_custom_var(r2, key)
    )


def cmp_ip_address(column: ColumnName, r1: Row, r2: Row) -> int:
    return compare_ips(r1.get(column, ""), r2.get(column, ""))


def compare_ips(ip1: str, ip2: str) -> int:
    def split_ip(ip: str) -> tuple:
        try:
            return tuple(int(part) for part in ip.split("."))
        except ValueError:
            # Make hostnames comparable with IPv4 address representations
            return (255, 255, 255, 255, ip)

    v1, v2 = split_ip(ip1), split_ip(ip2)
    return (v1 > v2) - (v1 < v2)


def get_custom_var(row: Row, key: str) -> str:
    return row["custom_variables"].get(key, "")


def join_row(row: Row, cell: "Cell") -> Row:
    if isinstance(cell, JoinCell):
        return row.get("JOIN", {}).get(cell.join_service())
    return row


def replace_action_url_macros(url: str, what: str, row: Row) -> str:
    macros = {
        "HOSTNAME": row["host_name"],
        "HOSTADDRESS": row["host_address"],
        "USER_ID": user.id,
    }
    if what == "service":
        macros.update(
            {
                "SERVICEDESC": row["service_description"],
            }
        )
    return replace_macros_in_str(
        url,
        {
            k_mod: v_mod
            for k_orig, v_orig in macros.items()
            for k_mod, v_mod in (
                (f"${k_orig}$", v_orig),
                (f"${k_orig}_URL_ENCODED$", urlencode(v_orig)),
            )
        },
    )


def render_cache_info(what: str, row: Row) -> str:
    cached_at = row["service_cached_at"]
    cache_interval = row["service_cache_interval"]
    cache_age = time.time() - cached_at

    text = _("Cache generated %s ago, cache interval: %s") % (
        cmk.utils.render.approx_age(cache_age),
        cmk.utils.render.approx_age(cache_interval),
    )

    if cache_interval:
        percentage = 100.0 * cache_age / cache_interval
        text += _(", elapsed cache lifespan: %s") % cmk.utils.render.percent(percentage)

    return text


# .
#   .--Cells---------------------------------------------------------------.
#   |                           ____     _ _                               |
#   |                          / ___|___| | |___                           |
#   |                         | |   / _ \ | / __|                          |
#   |                         | |__|  __/ | \__ \                          |
#   |                          \____\___|_|_|___/                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | View cell handling classes. Each cell instanciates a multisite       |
#   | painter to render a table cell.                                      |
#   '----------------------------------------------------------------------'


def painter_exists(painter_spec: PainterSpec) -> bool:
    return painter_spec.name in painter_registry


class Cell:
    """A cell is an instance of a painter in a view (-> a cell or a grouping cell)"""

    def __init__(
        self,
        view_spec: ViewSpec,
        view_user_sorters: list[SorterSpec] | None,
        painter_spec: PainterSpec | None = None,
    ) -> None:
        self._view_spec = view_spec
        self._view_user_sorters = view_user_sorters
        self._painter_name: PainterName | None = None
        self._painter_params: PainterParameters | None = None
        self._link_spec: VisualLinkSpec | None = None
        self._tooltip_painter_name: PainterName | None = None
        self._custom_title: str | None = None

        if painter_spec:
            self._from_view(painter_spec)

    def _from_view(self, painter_spec: PainterSpec) -> None:
        self._painter_name = painter_spec.name
        if painter_spec.parameters is not None:
            self._painter_params = painter_spec.parameters
            self._custom_title = self._painter_params.get("column_title", None)

        self._link_spec = painter_spec.link_spec

        tooltip_painter_name = painter_spec.tooltip
        if tooltip_painter_name is not None and tooltip_painter_name in painter_registry:
            self._tooltip_painter_name = tooltip_painter_name

    def needed_columns(self, permitted_views: Mapping[ViewName, ViewSpec]) -> set[ColumnName]:
        """Get a list of columns we need to fetch in order to render this cell"""

        columns = set(self.painter().columns)

        link_view = self._link_view(permitted_views)
        if link_view:
            # TODO: Clean this up here
            for filt in [
                visuals.get_filter(fn)
                for fn in visuals.get_single_info_keys(link_view["single_infos"])
            ]:
                columns.update(filt.link_columns)

        if self.has_tooltip():
            columns.update(self.tooltip_painter().columns)

        return columns

    def is_joined(self) -> bool:
        return False

    def join_service(self) -> ServiceName | None:
        return None

    def _link_view(self, permitted_views: Mapping[ViewName, ViewSpec]) -> ViewSpec | None:
        if self._link_spec is None:
            return None

        try:
            return permitted_views[self._link_spec.name]
        except KeyError:
            return None

    def painter(self) -> Painter:
        try:
            return PainterAdapter(experimental_painter_registry[self.painter_name()])
        except KeyError:
            return painter_registry[self.painter_name()]()

    def painter_name(self) -> PainterName:
        assert self._painter_name is not None
        return self._painter_name

    def export_title(self) -> str:
        if self._custom_title:
            return re.sub(r"[^\w]", "_", self._custom_title.lower())
        return self.painter().export_title(self)

    def painter_options(self) -> list[str]:
        return self.painter().painter_options

    def painter_parameters(self) -> Any:
        """The parameters configured in the view for this painter. In case the
        painter has params, it defaults to the valuespec default value and
        in case the painter has no params, it returns None."""
        vs_painter_params = self.painter().parameters
        if not vs_painter_params:
            return None

        if self._painter_params is None:
            return vs_painter_params.default_value()

        return self._painter_params

    def title(self, use_short: bool = True) -> str:
        if self._custom_title:
            return self._custom_title

        painter = self.painter()
        if use_short:
            return self._get_short_title(painter)
        return self._get_long_title(painter)

    def _get_short_title(self, painter: Painter) -> str:
        return painter.short_title(self)

    def _get_long_title(self, painter: Painter) -> str:
        return painter.title(self)

    # Can either be:
    # True       : Is printable in PDF
    # False      : Is not printable at all
    # "<string>" : ID of a painter_printer (Reporting module)
    def printable(self) -> bool | str:
        return self.painter().printable

    def has_tooltip(self) -> bool:
        return self._tooltip_painter_name is not None

    def tooltip_painter_name(self) -> str:
        assert self._tooltip_painter_name is not None
        return self._tooltip_painter_name

    def tooltip_painter(self) -> Painter:
        assert self._tooltip_painter_name is not None
        return painter_registry[self._tooltip_painter_name]()

    def paint_as_header(self) -> None:
        # Optional: Sort link in title cell
        # Use explicit defined sorter or implicit the sorter with the painter name
        # Important for links:
        # - Add the display options (Keeping the same display options as current)
        # - Link to _self (Always link to the current frame)
        classes: list[str] = []
        onclick = ""
        title = ""
        if (
            display_options.enabled(display_options.L)
            and self._view_spec.get("user_sortable", False)
            and _get_sorter_name_of_painter(self.painter_name()) is not None
        ):
            params: HTTPVariables = [
                ("sort", self._sort_url()),
                ("_show_filter_form", 0),
            ]
            if display_options.title_options:
                params.append(("display_options", display_options.title_options))

            classes += ["sort"]
            onclick = "location.href='%s'" % makeuri(request, addvars=params, remove_prefix="sort")
            title = _("Sort by %s") % self.title()
        classes += self.painter().title_classes()

        html.open_th(class_=classes, onclick=onclick, title=title)
        html.write_text(self.title())
        html.close_th()

    def _sort_url(self) -> str:
        """
        The following sorters need to be handled in this order:

        1. group by sorter (needed in grouped views)
        2. user defined sorters (url sorter)
        3. configured view sorters
        """
        sorter = []

        group_sort, user_sort, view_sort = _get_separated_sorters(
            self._view_spec, self._view_user_sorters
        )

        sorter = group_sort + user_sort + view_sort

        # Now apply the sorter of the current column:
        # - Negate/Disable when at first position
        # - Move to the first position when already in sorters
        # - Add in the front of the user sorters when not set
        painter_name = self.painter_name()
        sorter_name = _get_sorter_name_of_painter(painter_name)
        if sorter_name is None:
            # Do not change anything in case there is no sorter for the current column
            return _encode_sorter_url(sorter)

        if painter_name in ["svc_metrics_hist", "svc_metrics_forecast"]:
            uuid = ":%s" % self.painter_parameters()["uuid"]
            assert sorter_name is not None
            sorter_name += uuid
        elif painter_name in {"host_custom_variable"}:
            sorter_name = f'{sorter_name}:{self.painter_parameters()["ident"]}'

        this_asc_sorter = SorterSpec(sorter=sorter_name, negate=False, join_key=self.join_service())
        this_desc_sorter = SorterSpec(sorter=sorter_name, negate=True, join_key=self.join_service())

        if user_sort and this_asc_sorter == user_sort[0]:
            # Second click: Change from asc to desc order
            sorter[sorter.index(this_asc_sorter)] = this_desc_sorter

        elif user_sort and this_desc_sorter == user_sort[0]:
            # Third click: Remove this sorter
            sorter.remove(this_desc_sorter)

        else:
            # First click: add this sorter as primary user sorter
            # Maybe the sorter is already in the user sorters or view sorters, remove it
            for s in [user_sort, view_sort]:
                if this_asc_sorter in s:
                    s.remove(this_asc_sorter)
                if this_desc_sorter in s:
                    s.remove(this_desc_sorter)
            # Now add the sorter as primary user sorter
            sorter = group_sort + [this_asc_sorter] + user_sort + view_sort

        return _encode_sorter_url(sorter)

    def render(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
    ) -> tuple[str, str | HTML]:
        row = join_row(row, self)

        try:
            tdclass, content = self.render_content(row)
            assert isinstance(content, (str, HTML))
        except Exception:
            logger.exception("Failed to render painter '%s' (Row: %r)", self._painter_name, row)
            raise

        if tdclass is None:
            tdclass = ""

        if tdclass == "" and content == "":
            return "", ""

        # Add the optional link to another view
        if content and self._link_spec is not None and self._use_painter_link() and link_renderer:
            content = link_renderer(content, row, self._link_spec)

        # Add the optional mouseover tooltip
        if content and self.has_tooltip():
            assert isinstance(content, (str, HTML))
            tooltip_cell = Cell(
                self._view_spec,
                self._view_user_sorters,
                PainterSpec(self.tooltip_painter_name()),
            )
            _tooltip_tdclass, tooltip_content = tooltip_cell.render_content(row)
            assert not isinstance(tooltip_content, Mapping)
            tooltip_text = escaping.strip_tags_for_tooltip(tooltip_content)
            if tooltip_text:
                content = HTMLWriter.render_span(content, title=tooltip_text)

        return tdclass, content

    def _use_painter_link(self) -> bool:
        return self.painter().use_painter_link

    # Same as self.render() for HTML output: Gets a painter and a data
    # row and creates the text for being painted.
    def render_for_pdf(self, row: Row, time_range: TimeRange) -> PDFCellSpec:
        # TODO: Move this somewhere else!
        def find_htdocs_image_path(filename):
            themes = theme.icon_themes()
            for file_path in [
                cmk.utils.paths.local_web_dir / "htdocs" / filename,
                Path(cmk.utils.paths.web_dir, "htdocs", filename),
            ]:
                for path_in_theme in (str(file_path).replace(t, "facelift") for t in themes):
                    if os.path.exists(path_in_theme):
                        return path_in_theme
            return None

        try:
            row = join_row(row, self)
            css_classes, rendered_txt = self.render_content(row)
            if css_classes is None:
                css_classes = ""
            if rendered_txt is None:
                return css_classes, ""
            assert isinstance(rendered_txt, (str, HTML))

            txt = rendered_txt.strip()
            content: PDFCellContent = ""

            # Handle <img...>. Our PDF writer cannot draw arbitrary
            # images, but all that we need for showing simple icons.
            # Current limitation: *one* image
            assert not isinstance(txt, tuple)
            if (isinstance(txt, str) and txt.lower().startswith("<img")) or (
                isinstance(txt, HTML) and txt.lower().startswith(HTML("<img"))
            ):
                img_filename = re.sub(".*src=[\"']([^'\"]*)[\"'].*", "\\1", str(txt))
                img_path = find_htdocs_image_path(img_filename)
                if img_path:
                    content = ("icon", img_path)
                else:
                    content = img_filename

            if isinstance(txt, HTML):
                content = escaping.strip_tags(str(txt))

            elif not isinstance(txt, tuple):
                content = escaping.strip_tags(unescape(txt))

            return css_classes, content
        except Exception:
            raise MKGeneralException(
                'Failed to paint "%s": %s' % (self.painter_name(), traceback.format_exc())
            )

    # TODO render_for_python_export/as PDF

    def render_for_csv_export(self, row: Row) -> str | HTML:
        if request.var("output_format") not in ["csv", "csv_export"]:
            return "NOT_CSV_EXPORTABLE"

        if not row:
            return ""

        try:
            content = self.painter().export_for_csv(row, self)
        except CSVExportError:
            return "NOT_CSV_EXPORTABLE"

        return self._render_html_content(content)

    def render_for_json_export(self, row: Row) -> object:
        if request.var("output_format") not in ["json", "json_export"]:
            return "NOT_JSON_EXPORTABLE"

        if not row:
            return ""

        try:
            content = self.painter().export_for_json(row, self)
        except JSONExportError:
            return "NOT_JSON_EXPORTABLE"

        if isinstance(content, (str, HTML)):
            # TODO At the moment we have to keep this str/HTML handling because export_for_json
            # falls back to render. As soon as all painters have explicit export_for_* methods,
            # we can remove this...
            return self._render_html_content(content)

        return content

    def _render_html_content(self, content: str | HTML) -> str:
        txt: str = str(content).strip()

        # Similar to the PDF rendering hack above, but this time we extract the title from our icons
        # and add them to the CSV export instead of stripping the whole HTML tag.
        # Current limitation: *one* image
        if txt.lower().startswith("<img"):
            txt = re.sub(".*title=[\"']([^'\"]*)[\"'].*", "\\1", str(txt))

        return txt

    def render_content(self, row: Row) -> CellSpec:
        if not row:
            return "", ""  # nothing to paint

        painter = self.painter()
        return painter.render(row, self)

    def paint(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
        colspan: int | None = None,
    ) -> bool:
        tdclass, content = self.render(row, link_renderer)
        assert isinstance(content, (str, HTML))
        html.td(content, class_=tdclass, colspan=colspan)
        return content != ""


def _encode_sorter_url(sorters: Iterable[SorterSpec]) -> str:
    p: list[str] = []
    for s in sorters:
        sorter_name = s.sorter
        if not isinstance(sorter_name, str):
            # sorter_name is a tuple
            if sorter_name[0] in {"host_custom_variable"}:
                sorter_name, params = sorter_name
                sorter_name = "{}:{}".format(sorter_name, params["ident"])
            else:
                raise MKGeneralException(f"Can not handle sorter {sorter_name}")
        url = ("-" if s.negate else "") + sorter_name
        if s.join_key:
            url += "~" + s.join_key
        p.append(url)

    return ",".join(p)


class JoinCell(Cell):
    def __init__(
        self,
        view_spec: ViewSpec,
        view_user_sorters: list[SorterSpec] | None,
        painter_spec: PainterSpec,
    ) -> None:
        self._join_service_descr: ServiceName | None = None
        super().__init__(view_spec, view_user_sorters, painter_spec)

    def _from_view(self, painter_spec: PainterSpec) -> None:
        super()._from_view(painter_spec)

        self._join_service_descr = painter_spec.join_index

        if painter_spec.column_title and self._custom_title is None:
            self._custom_title = painter_spec.column_title

    def is_joined(self) -> bool:
        return True

    def join_service(self) -> ServiceName:
        assert self._join_service_descr is not None
        return self._join_service_descr

    def livestatus_filter(self, join_column_name: str) -> LivestatusQuery:
        return "Filter: %s = %s" % (
            livestatus.lqencode(join_column_name),
            livestatus.lqencode(self.join_service()),
        )

    def title(self, use_short: bool = True) -> str:
        return self._custom_title or self.join_service()

    def export_title(self) -> str:
        serv_painter = re.sub(r"[^\w]", "_", self.title().lower())
        return "%s.%s" % (self._painter_name, serv_painter)


class EmptyCell(Cell):
    def render(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
    ) -> tuple[str, str]:
        return "", ""

    def paint(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
        colspan: int | None = None,
    ) -> bool:
        return False


def output_csv_headers(view: ViewSpec) -> None:
    filename = "%s-%s.csv" % (
        view["name"],
        time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time())),
    )
    response.headers["Content-Disposition"] = 'Attachment; filename="%s"' % filename


def _get_sorter_name_of_painter(
    painter_name_or_spec: PainterName | PainterSpec,
) -> SorterName | None:
    painter_name = (
        painter_name_or_spec.name
        if isinstance(painter_name_or_spec, PainterSpec)
        else painter_name_or_spec
    )
    painter = painter_registry[painter_name]()
    if painter.sorter:
        return painter.sorter

    if painter_name in sorter_registry:
        return painter_name

    return None


def _substract_sorters(base: list[SorterSpec], remove: list[SorterSpec]) -> None:
    for s in remove:
        negated_sorter = SorterSpec(sorter=s.sorter, negate=not s.negate, join_key=None)

        if s in base:
            base.remove(s)
        elif negated_sorter in base:
            base.remove(negated_sorter)


def _get_group_sorters(view_spec: ViewSpec) -> list[SorterSpec]:
    group_sort: list[SorterSpec] = []
    for p in view_spec["group_painters"]:
        if not painter_exists(p):
            continue
        sorter_name = _get_sorter_name_of_painter(p)
        if sorter_name is None:
            continue

        group_sort.append(SorterSpec(sorter_name, negate=False, join_key=None))
    return group_sort


def _get_separated_sorters(
    view_spec: ViewSpec,
    view_user_sorters: list[SorterSpec] | None,
) -> tuple[list[SorterSpec], list[SorterSpec], list[SorterSpec]]:
    group_sort = _get_group_sorters(view_spec)
    view_sort = [
        s for s in view_spec["sorters"] if not any(s.sorter == gs.sorter for gs in group_sort)
    ]
    user_sort = view_user_sorters or []

    _substract_sorters(user_sort, group_sort)
    _substract_sorters(view_sort, user_sort)

    return group_sort, user_sort, view_sort


class PainterAdapter(Painter):
    def __init__(self, painter: V1Painter):
        self._painter = painter

    @property
    def ident(self) -> str:
        return self._painter.ident

    def title(self, cell: Cell) -> str:
        return str(self._painter.title)

    def short_title(self, cell: Cell) -> str:
        return str(self._painter.short_title)

    @property
    def columns(self) -> Sequence[ColumnName]:
        return self._painter.columns

    def dynamic_columns(self, cell: "Cell") -> list[ColumnName]:
        # TODO: the dynamic columns/derive functionality is added, once we migrate painters using it
        if self._painter.dynamic_columns is None:
            return []
        return list(self._painter.dynamic_columns(cell.painter_parameters()))

    @property
    def painter_options(self) -> list[str]:
        """Returns a list of painter option names that affect this painter"""
        return self._painter.painter_options or []

    def title_classes(self) -> list[str]:
        return self._painter.title_classes or []

    def render(self, row: Row, cell: Cell) -> CellSpec:
        config = PainterConfiguration(
            parameters=cell.painter_parameters(), columns=self._painter.columns
        )
        return self._painter.formatters.html(
            list(self._painter.computer([row], config))[0],
            cell.painter_parameters(),
        )
