#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for internals and the plugins"""

# TODO: More feature related splitting up would be better

import abc
import time
import re
import hashlib
from pathlib import Path
import traceback
from typing import Callable, NamedTuple, Hashable, TYPE_CHECKING, Any, Set, Tuple, List, Optional, Union, Dict, Type, cast

from six import ensure_str

import livestatus
from livestatus import SiteId, LivestatusColumn, LivestatusRow, OnlySites

import cmk.utils.plugin_registry
import cmk.utils.render
import cmk.utils.regex
from cmk.utils.type_defs import (
    Timestamp,
    TimeRange,
    HostName,
    TagGroups,
    LabelSources,
    ServiceName,
)

import cmk.gui.config as config
import cmk.gui.escaping as escaping
import cmk.gui.sites as sites
import cmk.gui.visuals as visuals
import cmk.gui.forms as forms
import cmk.gui.utils
import cmk.gui.view_utils
import cmk.gui.valuespec as valuespec
from cmk.gui.permissions import Permission
from cmk.gui.valuespec import ValueSpec, DropdownChoice
from cmk.gui.log import logger
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _, _u
from cmk.gui.globals import g, html, request
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.display_options import display_options
from cmk.gui.permissions import permission_registry
from cmk.gui.view_utils import CellSpec, CSSClass, CellContent
from cmk.gui.breadcrumb import make_topic_breadcrumb, Breadcrumb, BreadcrumbItem
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.pagetypes import PagetypeTopics

from cmk.gui.type_defs import (
    ColumnName,
    ViewName,
    LivestatusQuery,
    SorterName,
    HTTPVariables,
    ViewSpec,
    PainterSpec,
    PainterName,
    Row,
    Rows,
    SorterFunction,
    AllViewSpecs,
    PermittedViewSpecs,
    VisualContext,
    PainterParameters,
)

from cmk.gui.utils.urls import makeuri, makeuri_contextless

if TYPE_CHECKING:
    from cmk.gui.views import View
    from cmk.gui.plugins.visuals.utils import Filter

PDFCellContent = Union[str, HTML, Tuple[str, str]]
PDFCellSpec = Union[CellSpec, Tuple[CSSClass, PDFCellContent]]


# TODO: Better name it PainterOptions or DisplayOptions? There are options which only affect
# painters, but some which affect generic behaviour of the views, so DisplayOptions might
# be better.
class PainterOptions:
    """Painter options are settings that can be changed per user per view.
    These options are controlled throught the painter options form which
    is accessible through the small monitor icon on the top left of the
    views."""

    # TODO: We should have some View instance that uses an object of this class as helper instead,
    #       but this would be a bigger change involving a lot of view rendering code.
    @classmethod
    def get_instance(cls) -> 'PainterOptions':
        """Use the request globals to prevent multiple instances during a request"""
        if 'painter_options' not in g:
            g.painter_options = cls()
        return g.painter_options

    def __init__(self) -> None:
        super(PainterOptions, self).__init__()
        # The names of the painter options used by the current view
        self._used_option_names: List[str] = []
        # The effective options for this view
        self._options: Dict[str, Any] = {}

    def load(self, view_name: Optional[str] = None) -> None:
        self._load_from_config(view_name)

    # Load the options to be used for this view
    def _load_used_options(self, view: 'View') -> None:
        options: Set[str] = set()

        for cell in view.group_cells + view.row_cells:
            options.update(cell.painter_options())

        # Also layouts can register painter options
        layout_name = view.spec.get("layout")
        if layout_name is not None:
            layout_class = layout_registry.get(layout_name)
            if layout_class:
                options.update(layout_class().painter_options)

        # Mandatory options for all views (if permitted)
        if display_options.enabled(display_options.O):
            if display_options.enabled(
                    display_options.R) and config.user.may("general.view_option_refresh"):
                options.add("refresh")

            if config.user.may("general.view_option_columns"):
                options.add("num_columns")

        # TODO: Improve sorting. Add a sort index?
        self._used_option_names = sorted(options)

    def _load_from_config(self, view_name: Optional[str]) -> None:
        if self._is_anonymous_view(view_name):
            return  # never has options

        if not self.painter_options_permitted():
            return

        # Options are stored per view. Get all options for all views
        vo = config.user.load_file("viewoptions", {})
        self._options = vo.get(view_name, {})

    def _is_anonymous_view(self, view_name: Optional[str]) -> bool:
        return view_name is None

    def save_to_config(self, view_name: str) -> None:
        vo = config.user.load_file("viewoptions", {}, lock=True)
        vo[view_name] = self._options
        config.user.save_file("viewoptions", vo)

    def update_from_url(self, view: 'View') -> None:
        self._load_used_options(view)

        if not self.painter_option_form_enabled():
            return

        if html.request.has_var("_reset_painter_options"):
            self._clear_painter_options(view.name)
            return

        if html.request.has_var("_update_painter_options"):
            self._set_from_submitted_form(view.name)

    def _set_from_submitted_form(self, view_name: str) -> None:
        # TODO: Remove all keys that are in painter_option_registry
        # but not in self._used_option_names

        modified = False
        for option_name in self._used_option_names:
            # Get new value for the option from the value spec
            vs = self.get_valuespec_of(option_name)
            value = vs.from_html_vars("po_%s" % option_name)

            if not self._is_set(option_name) or self.get(option_name) != value:
                modified = True

            self.set(option_name, value)

        if modified:
            self.save_to_config(view_name)

    def _clear_painter_options(self, view_name: str) -> None:
        # TODO: This never removes options that are not existant anymore
        modified = False
        for name in painter_option_registry.keys():
            try:
                del self._options[name]
                modified = True
            except KeyError:
                pass

        if modified:
            self.save_to_config(view_name)

        # Also remove the options from current html vars. Otherwise the
        # painter option form will display the just removed options as
        # defaults of the painter option form.
        for varname, _value in list(html.request.itervars(prefix="po_")):
            html.request.del_var(varname)

    def get_valuespec_of(self, name: str) -> ValueSpec:
        return painter_option_registry[name]().valuespec

    def _is_set(self, name: str) -> bool:
        return name in self._options

    # Sets a painter option value (only for this request). Is not persisted!
    def set(self, name: str, value: Any) -> None:
        self._options[name] = value

    # Returns either the set value, the provided default value or if none
    # provided, it returns the default value of the valuespec.
    def get(self, name: str, dflt: Any = None) -> Any:
        if dflt is None:
            try:
                dflt = self.get_valuespec_of(name).default_value()
            except KeyError:
                # Some view options (that are not declared as display options)
                # like "refresh" don't have a valuespec. So they need to default
                # to None.
                # TODO: Find all occurences and simply declare them as "invisible"
                # painter options.
                pass
        return self._options.get(name, dflt)

    # Not falling back to a default value, simply returning None in case
    # the option is not set.
    def get_without_default(self, name: str) -> Any:
        return self._options.get(name)

    def get_all(self) -> Dict[str, Any]:
        return self._options

    def painter_options_permitted(self) -> bool:
        return config.user.may("general.painter_options")

    def painter_option_form_enabled(self) -> bool:
        return bool(self._used_option_names) and self.painter_options_permitted()

    def show_form(self, view: 'View') -> None:
        self._load_used_options(view)

        if not display_options.enabled(display_options.D) or not self.painter_option_form_enabled():
            return

        html.begin_form("painteroptions")
        forms.header(_("Display options"))
        for name in self._used_option_names:
            vs = self.get_valuespec_of(name)
            forms.section(vs.title())
            # TODO: Possible improvement for vars which default is specified
            # by the view: Don't just default to the valuespecs default. Better
            # use the view default value here to get the user the current view
            # settings reflected.
            vs.render_input("po_%s" % name, self.get(name))
        forms.end()

        html.button("_update_painter_options", _("Submit"), "submit")
        html.button("_reset_painter_options", _("Reset"), "submit")

        html.hidden_fields()
        html.end_form()


def row_id(view_spec: Dict[str, Any], row: Row) -> str:
    """Calculates a uniq id for each data row which identifies the current
    row accross different page loadings."""
    key = u''
    for col in data_source_registry[view_spec['datasource']]().id_keys:
        key += u'~%s' % row[col]
    return ensure_str(hashlib.sha256(key.encode('utf-8')).hexdigest())


def group_value(row: Row, group_cells: 'List[Cell]') -> Hashable:
    """The Group-value of a row is used for deciding whether
    two rows are in the same group or not"""
    group = []
    for cell in group_cells:
        painter = cell.painter()

        group_by_val = painter.group_by(row)
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
        return tuple([(k, _create_dict_key(v)) for (k, v) in sorted(value.items())])
    return value


class PainterOption(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def ident(self) -> str:
        """The identity of a painter option. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def valuespec(self) -> ValueSpec:
        raise NotImplementedError()


class ViewPainterOptionRegistry(cmk.utils.plugin_registry.Registry[Type[PainterOption]]):
    def plugin_name(self, instance: Type[PainterOption]) -> str:
        return instance().ident


painter_option_registry = ViewPainterOptionRegistry()


@painter_option_registry.register
class PainterOptionRefresh(PainterOption):
    @property
    def ident(self):
        return "refresh"

    @property
    def valuespec(self):
        choices = [(x, {0: _("off")}.get(x, str(x) + "s")) for x in config.view_option_refreshes]
        return DropdownChoice(
            title=_("Refresh interval"),
            choices=choices,
        )


@painter_option_registry.register
class PainterOptionNumColumns(PainterOption):
    @property
    def ident(self):
        return "num_columns"

    @property
    def valuespec(self):
        return DropdownChoice(
            title=_("Number of columns"),
            choices=[(x, str(x)) for x in config.view_option_columns],
        )


class Layout(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def ident(self) -> str:
        """The identity of a layout. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        """Short human readable title of the layout"""
        raise NotImplementedError()

    @abc.abstractmethod
    def render(self, rows: Rows, view: Dict, group_cells: 'List[Cell]', cells: 'List[Cell]',
               num_columns: int, show_checkboxes: bool) -> None:
        """Render the given data in this layout"""
        raise NotImplementedError()

    @abc.abstractproperty
    def can_display_checkboxes(self) -> bool:
        """Whether this layout can display checkboxes for selecting rows"""
        raise NotImplementedError()

    @property
    def painter_options(self) -> List[str]:
        """Returns the painter option identities used by this layout"""
        return []

    @property
    def has_individual_csv_export(self) -> bool:
        """Whether this layout has an individual CSV export implementation"""
        return False

    def csv_export(self, rows: Rows, view: Dict, group_cells: 'List[Cell]',
                   cells: 'List[Cell]') -> None:
        """Render the given data using this layout for CSV"""


class ViewLayoutRegistry(cmk.utils.plugin_registry.Registry[Type[Layout]]):
    def plugin_name(self, instance: Type[Layout]) -> str:
        return instance().ident

    def get_choices(self) -> List[Tuple[str, str]]:
        choices = []
        for plugin_class in self.values():
            layout = plugin_class()
            choices.append((layout.ident, layout.title))

        return choices


layout_registry = ViewLayoutRegistry()

Exporter = NamedTuple("Exporter", [
    ("name", str),
    ("handler", Callable[["View", Rows], None]),
])


class ViewExporterRegistry(cmk.utils.plugin_registry.Registry[Exporter]):
    def plugin_name(self, instance):
        return instance.name


exporter_registry = ViewExporterRegistry()


class CommandGroup(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def ident(self) -> str:
        """The identity of a command group. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def sort_index(self) -> int:
        raise NotImplementedError()


class CommandGroupRegistry(cmk.utils.plugin_registry.Registry[Type[CommandGroup]]):
    def plugin_name(self, instance: Type[CommandGroup]) -> str:
        return instance().ident


command_group_registry = CommandGroupRegistry()


# TODO: Kept for pre 1.6 compatibility
def register_command_group(ident: str, title: str, sort_index: int) -> None:
    cls = type(
        "LegacyCommandGroup%s" % ident.title(), (CommandGroup,), {
            "_ident": ident,
            "_title": title,
            "_sort_index": sort_index,
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._title),
            "sort_index": property(lambda s: s._sort_index),
        })
    command_group_registry.register(cls)


class Command(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def ident(self) -> str:
        """The identity of a command. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def permission(self) -> Permission:
        raise NotImplementedError()

    @abc.abstractproperty
    def tables(self) -> List[str]:
        """List of livestatus table identities the action may be used with"""
        raise NotImplementedError()

    def render(self, what: str) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def action(self, cmdtag: str, spec: str, row: dict, row_index: int,
               num_rows: int) -> Optional[Tuple[Union[str, List[str]], str]]:
        raise NotImplementedError()

    @property
    def group(self) -> Type[CommandGroup]:
        """The command group the commmand belongs to"""
        return command_group_registry["various"]

    @property
    def only_view(self) -> Optional[str]:
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

    def executor(self, command: str, site: str) -> None:
        """Function that is called to execute this action"""
        sites.live().command("[%d] %s" % (int(time.time()), command), SiteId(site))


class CommandRegistry(cmk.utils.plugin_registry.Registry[Type[Command]]):
    def plugin_name(self, instance: Type[Command]) -> str:
        return instance().ident


command_registry = CommandRegistry()


# TODO: Kept for pre 1.6 compatibility
def register_legacy_command(spec: Dict[str, Any]) -> None:
    ident = re.sub("[^a-zA-Z]", "", spec["title"]).lower()
    cls = type(
        "LegacyCommand%s" % str(ident).title(), (Command,), {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._spec["title"]),
            "permission": property(lambda s: permission_registry[s._spec["permission"]]),
            "tables": property(lambda s: s._spec["tables"]),
            "render": lambda s: s._spec["render"](),
            "action": lambda s, cmdtag, spec, row, row_index, num_rows: s._spec["action"]
                      (cmdtag, spec, row),
            "group": lambda s: command_group_registry[s._spec.get("group", "various")],
            "only_view": lambda s: s._spec.get("only_view"),
        })
    command_registry.register(cls)


class ABCDataSource(metaclass=abc.ABCMeta):
    """Provider of rows for the views (basically tables of data) in the GUI"""
    @abc.abstractproperty
    def ident(self) -> str:
        """The identity of a data source. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        """Used as display-string for the datasource in the GUI (e.g. view editor)"""
        raise NotImplementedError()

    @abc.abstractproperty
    def table(self) -> 'RowTable':
        """Returns a table object that can provide a list of rows for the provided
        query using the query() method."""
        raise NotImplementedError()

    @abc.abstractproperty
    def infos(self) -> List[str]:
        """Infos that are available with this data sources

        A info is used to create groups out of single painters and filters.
        e.g. 'host' groups all painters and filters which begin with "host_".
        Out of this declaration multisite knows which filters or painters are
        available for the single datasources."""
        raise NotImplementedError()

    @property
    def merge_by(self) -> Optional[str]:
        """
        1. Results in fetching these columns from the datasource.
        2. Rows from different sites are merged together. For example members
           of hostgroups which exist on different sites are merged together to
           show the user one big hostgroup.
        """
        return None

    @property
    def add_columns(self) -> List[ColumnName]:
        """These columns are requested automatically in addition to the
        other needed columns."""
        return []

    @property
    def add_headers(self) -> str:
        """additional livestatus headers to add to each call"""
        return ""

    @abc.abstractproperty
    def keys(self) -> List[ColumnName]:
        """columns which must be fetched in order to execute commands on
        the items (= in order to identify the items and gather all information
        needed for constructing Nagios commands)
        those columns are always fetched from the datasource for each item"""
        raise NotImplementedError()

    @abc.abstractproperty
    def id_keys(self) -> List[ColumnName]:
        """These are used to generate a key which is unique for each data row
        is used to identify an item between http requests"""
        raise NotImplementedError()

    @property
    def join(self) -> Optional[Tuple]:
        """A view can display e.g. host-rows and include information from e.g.
        the service table to create a column which shows e.g. the state of one
        service.
        With this attibute it is configured which tables can be joined into
        this table and by which attribute. It must be given as tuple, while
        the first argument is the name of the table to be joined and the second
        argument is the column in the master table (in this case hosts) which
        is used to match the rows of the master and slave table."""
        return None

    @property
    def join_key(self) -> Optional[str]:
        """Each joined column in the view can have a 4th attribute which is
        used as value for this column to filter the datasource query
        to get the matching row of the slave table."""
        return None

    @property
    def ignore_limit(self) -> bool:
        """Ignore the soft/hard query limits in view.py/query_data(). This
        fixes stats queries on e.g. the log table."""
        return False

    @property
    def auth_domain(self) -> str:
        """Querying a table might require to use another auth domain than
        the default one (read). When this is set, the given auth domain
        will be used while fetching the data for this datasource from
        livestatus."""
        return "read"

    @property
    def time_filters(self) -> List[str]:
        return []

    @property
    def link_filters(self) -> Dict[str, str]:
        """When the single info "hostgroup" is used, use the "opthostgroup" filter
        to handle the data provided by the single_spec value of the "hostgroup"
        info, which is in fact the name of the wanted hostgroup"""
        return {}

    # TODO: This can be cleaned up later
    def post_process(self, rows: Rows) -> Rows:
        """Optional function to postprocess the resulting data after executing
        the regular data fetching"""
        return rows


class DataSourceLivestatus(ABCDataSource):
    """Base class for all simple data sources which 1:1 base on a livestatus table"""
    @property
    def table(self) -> 'RowTableLivestatus':
        return RowTableLivestatus(self.ident)


class DataSourceRegistry(cmk.utils.plugin_registry.Registry[Type[ABCDataSource]]):
    def plugin_name(self, instance: Type[ABCDataSource]) -> str:
        return instance().ident

    # TODO: Sort the datasources by (assumed) common usage
    def data_source_choices(self) -> List[Tuple[str, str]]:
        datasources = []
        for ident, ds_class in self.items():
            datasources.append((ident, ds_class().title))
        return sorted(datasources, key=lambda x: x[1])


data_source_registry = DataSourceRegistry()


class RowTable(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def query(self, view: 'View', columns: List[ColumnName], headers: str, only_sites: OnlySites,
              limit: Optional[int], all_active_filters: 'List[Filter]') -> Rows:
        raise NotImplementedError()


class RowTableLivestatus(RowTable):
    def __init__(self, table_name: str) -> None:
        super(RowTableLivestatus, self).__init__()
        self._table_name = table_name

    @property
    def table_name(self) -> str:
        return self._table_name

    @staticmethod
    def _prepare_columns(columns: List[ColumnName],
                         view: 'View') -> Tuple[List[ColumnName], Dict[int, List[ColumnName]]]:
        dynamic_columns = {}
        for index, cell in enumerate(view.row_cells):
            dyn_col = cell.painter().dynamic_columns(cell)
            dynamic_columns[index] = dyn_col
            columns += dyn_col

        columns = list(set(columns))

        datasource = view.datasource
        merge_column = datasource.merge_by
        if merge_column:
            # Prevent merge column from being duplicated in the query. It needs
            # to be at first position, see _merge_data()
            columns = [merge_column] + [c for c in columns if c != merge_column]

        # Most layouts need current state of object in order to
        # choose background color - even if no painter for state
        # is selected. Make sure those columns are fetched. This
        # must not be done for the table 'log' as it cannot correctly
        # distinguish between service_state and host_state
        if "log" not in datasource.infos:
            state_columns: List[ColumnName] = []
            if "service" in datasource.infos:
                state_columns += ["service_has_been_checked", "service_state"]
            if "host" in datasource.infos:
                state_columns += ["host_has_been_checked", "host_state"]
            for c in state_columns:
                if c not in columns:
                    columns.append(c)

        # Remove columns which are implicitely added by the datasource
        return [c for c in columns if c not in datasource.add_columns], dynamic_columns

    def prepare_lql(self, columns: List[ColumnName], headers: str) -> LivestatusQuery:
        query = "GET %s\n" % self.table_name
        query += "Columns: %s\n" % " ".join(columns)
        query += headers
        return query

    def query(self, view: 'View', columns: List[ColumnName], headers: str, only_sites: OnlySites,
              limit: Optional[int], all_active_filters: 'List[Filter]') -> Rows:
        """Retrieve data via livestatus, convert into list of dicts,

        view: view object
        columns: the list of livestatus columns to query
        headers: query headers
        only_sites: list of sites the query is limited to
        limit: maximum number of data rows to query
        all_active_filters: Momentarily unused
        """

        datasource = view.datasource

        columns, dynamic_columns = self._prepare_columns(columns, view)
        query = self.prepare_lql(columns, headers + datasource.add_headers)
        data = query_livestatus(query, only_sites, limit, datasource.auth_domain)

        if datasource.merge_by:
            data = _merge_data(data, columns)

        # convert lists-rows into dictionaries.
        # performance, but makes live much easier later.
        columns = ["site"] + columns + datasource.add_columns
        rows: Rows = datasource.post_process([dict(zip(columns, row)) for row in data])

        for index, cell in enumerate(view.row_cells):
            painter = cell.painter()
            painter.derive(rows, cell, dynamic_columns.get(index))

        return rows


def query_livestatus(query: LivestatusQuery, only_sites: OnlySites, limit: Optional[int],
                     auth_domain: str) -> List[LivestatusRow]:

    if all((
            config.debug_livestatus_queries,
            html.output_format == "html",
            display_options.enabled(display_options.W),
    )):
        html.open_div(class_=["livestatus", "message"])
        html.tt(query.replace('\n', '<br>\n'))
        html.close_div()

    sites.live().set_auth_domain(auth_domain)
    with sites.only_sites(only_sites), sites.prepend_site(), sites.set_limit(limit):
        data = sites.live().query(query)

    sites.live().set_auth_domain("read")

    return data


# TODO: Return value of render() could be cleaned up e.g. to a named tuple with an
# optional CSS class. A lot of painters don't specify CSS classes.
# TODO: Since we have the reporting also working with the painters it could be useful
# to make the render function return structured data which can then be rendered for
# HTML and PDF.
# TODO: A lot of painter classes simply display plain livestatus column values. These
# could be replaced with some simpler generic definition.
class Painter(metaclass=abc.ABCMeta):
    """A painter computes HTML code based on information from a data row and
    creates a CSS class for one display column.

    Please note, that there is no
    1:1 relation between data columns and display columns. A painter can
    make use of more than one data columns. One example is the current
    service state. It uses the columns "service_state" and "has_been_checked".
    """
    @abc.abstractproperty
    def ident(self) -> str:
        """The identity of a painter. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractmethod
    def title(self, cell: 'Cell') -> str:
        """Used as display string for the painter in the GUI (e.g. views using this painter)"""
        raise NotImplementedError()

    @abc.abstractproperty
    def columns(self) -> List[ColumnName]:
        """Livestatus columns needed for this painter"""
        raise NotImplementedError()

    def dynamic_columns(self, cell: 'Cell') -> List[ColumnName]:
        """Return list of dynamically generated column as specified by Cell

        Some columns for the Livestatus query need to be generated at
        execution time, knowing user configuration. Using the Cell object
        generated the required column names."""
        return []

    def derive(self, rows: Rows, cell: 'Cell', dynamic_columns: Optional[List[ColumnName]]) -> None:
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
        dynamic_columns: List[str]
            The exact dynamic columns generated by the painter before the
            query. As they might be required to find them again within the
            data."""

    @abc.abstractmethod
    def render(self, row: Row, cell: 'Cell') -> CellSpec:
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

    def short_title(self, cell: 'Cell') -> str:
        """Used as display string for the painter e.g. as table header
        Falls back to the full title if no short title is given"""
        return self.title(cell)

    def list_title(self, cell: 'Cell') -> str:
        """Override this to define a custom title for the painter in the view editor
        Falls back to the full title if no short title is given"""
        return self.title(cell)

    def group_by(self, row: Row) -> Union[None, str, Tuple]:
        """When a value is returned, this is used instead of the value produced by self.paint()"""
        return None

    @property
    def parameters(self) -> Optional[ValueSpec]:
        """Returns either the valuespec of the painter parameters or None"""
        return None

    @property
    def painter_options(self) -> List[str]:
        """Returns a list of painter option names that affect this painter"""
        return []

    @property
    def printable(self) -> Union[bool, str]:
        """
        True       : Is printable in PDF
        False      : Is not printable at all
        "<string>" : ID of a painter_printer (Reporting module)
        """
        return True

    @property
    def sorter(self) -> Optional[SorterName]:
        """Returns the optional name of the sorter for this painter"""
        return None

    # TODO: Cleanup this hack
    @property
    def load_inv(self) -> bool:
        """Whether or not to load the HW/SW inventory for this column"""
        return False


class PainterRegistry(cmk.utils.plugin_registry.Registry[Type[Painter]]):
    def plugin_name(self, instance: Type[Painter]) -> str:
        return instance().ident


painter_registry = PainterRegistry()


# Kept for pre 1.6 compatibility. But also the inventory.py uses this to
# register some painters dynamically
def register_painter(ident: str, spec: Dict[str, Any]) -> None:
    cls = type(
        "LegacyPainter%s" % ident.title(), (Painter,), {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": lambda s, cell: s._spec["title"],
            "short_title": lambda s, cell: s._spec.get("short", s.title),
            "columns": property(lambda s: s._spec["columns"]),
            "render": lambda self, row, cell: spec["paint"](row),
            "group_by": lambda self, row: self._spec.get("groupby"),
            "parameters": property(lambda s: s._spec.get("params")),
            "painter_options": property(lambda s: s._spec.get("options", [])),
            "printable": property(lambda s: s._spec.get("printable", True)),
            "sorter": property(lambda s: s._spec.get("sorter", None)),
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),
        })
    painter_registry.register(cls)


class Sorter(metaclass=abc.ABCMeta):
    """A sorter is used for allowing the user to sort the queried data
    according to a certain logic."""
    @abc.abstractproperty
    def ident(self) -> str:
        """The identity of a sorter. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        """Used as display string for the sorter in the GUI (e.g. view editor)"""
        raise NotImplementedError()

    @abc.abstractproperty
    def columns(self) -> List[str]:
        """Livestatus columns needed for this sorter"""
        raise NotImplementedError()

    @abc.abstractmethod
    def cmp(self, r1: Dict, r2: Dict) -> int:
        """The function cmp does the actual sorting. During sorting it
        will be called with two data rows as arguments and must
        return -1, 0 or 1:

        -1: The first row is smaller than the second (should be output first)
         0: Both rows are equivalent
         1: The first row is greater than the second.

        The rows are dictionaries from column names to values. Each row
        represents one item in the Livestatus table, for example one host,
        one service, etc."""
        raise NotImplementedError()

    @property
    def _args(self) -> Optional[List]:
        """Optional list of arguments for the cmp function"""
        return None

    # TODO: Cleanup this hack
    @property
    def load_inv(self) -> bool:
        """Whether or not to load the HW/SW inventory for this column"""
        return False


class DerivedColumnsSorter(Sorter):
    @abc.abstractmethod
    def derived_columns(self, view: 'View', uuid: Optional[str]) -> List[str]:
        raise NotImplementedError()


class SorterRegistry(cmk.utils.plugin_registry.Registry[Type[Sorter]]):
    def plugin_name(self, instance: Type[Sorter]) -> str:
        return instance().ident


sorter_registry = SorterRegistry()


# Kept for pre 1.6 compatibility. But also the inventory.py uses this to
# register some painters dynamically
def register_sorter(ident: str, spec: Dict[str, Any]) -> None:
    cls = type(
        "LegacySorter%s" % str(ident).title(), (Sorter,), {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._spec["title"]),
            "columns": property(lambda s: s._spec["columns"]),
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),
            "cmp": spec["cmp"],
        })
    sorter_registry.register(cls)


# TODO: Refactor to plugin_registries
multisite_builtin_views: Dict = {}
view_hooks: Dict = {}
inventory_displayhints: Dict = {}
# For each view a function can be registered that has to return either True
# or False to show a view as context link
view_is_enabled: Dict = {}


def view_title(view_spec: ViewSpec) -> str:
    return visuals.visual_title('view', view_spec)


def transform_action_url(url_spec: Union[Tuple[str, str], str]) -> Tuple[str, Optional[str]]:
    if isinstance(url_spec, tuple):
        return url_spec
    return (url_spec, None)


def is_stale(row: Row) -> bool:
    staleness = row.get('service_staleness', row.get('host_staleness', 0)) or 0
    return staleness >= config.staleness_threshold


def paint_stalified(row: Row, text: CellContent) -> CellSpec:
    if is_stale(row):
        return "stale", text
    return "", text


def paint_host_list(site: SiteId, hosts: List[HostName]) -> CellSpec:
    return "", ", ".join(
        cmk.gui.view_utils.get_host_list_links(site, [ensure_str(h) for h in hosts]))


def format_plugin_output(output: CellContent, row: Row) -> str:
    return cmk.gui.view_utils.format_plugin_output(output,
                                                   row,
                                                   shall_escape=config.escape_plugin_output)


def link_to_view(content: CellContent, row: Row, view_name: ViewName) -> CellContent:
    assert not isinstance(content, dict)
    if display_options.disabled(display_options.I):
        return content

    url = url_to_view(row, view_name)
    if url:
        return html.render_a(content, href=url)
    return content


# TODO: There is duplicated logic with visuals.collect_context_links_of()
def url_to_view(row: Row, view_name: ViewName) -> Optional[str]:
    if display_options.disabled(display_options.I):
        return None

    view = get_permitted_views().get(view_name)
    if not view:
        return None

    # Get the context type of the view to link to, then get the parameters of this
    # context type and try to construct the context from the data of the row
    url_vars: HTTPVariables = []
    datasource = data_source_registry[view['datasource']]()
    for info_key in datasource.infos:
        if info_key in view['single_infos']:
            # Determine which filters (their names) need to be set
            # for specifying in order to select correct context for the
            # target view.
            for filter_name in visuals.info_params(info_key):
                filter_object = visuals.get_filter(filter_name)
                # Get the list of URI vars to be set for that filter
                new_vars = filter_object.variable_settings(row)
                url_vars += new_vars

    # See get_link_filter_names() comment for details
    for src_key, dst_key in visuals.get_link_filter_names(view, datasource.infos,
                                                          datasource.link_filters):
        try:
            url_vars += visuals.get_filter(src_key).variable_settings(row)
        except KeyError:
            pass

        try:
            url_vars += visuals.get_filter(dst_key).variable_settings(row)
        except KeyError:
            pass

    add_site_hint = visuals.may_add_site_hint(view_name,
                                              info_keys=datasource.infos,
                                              single_info_keys=view["single_infos"],
                                              filter_names=[v for v, _ in url_vars])
    if add_site_hint and row.get('site'):
        url_vars.append(('site', row['site']))

    do = html.request.var("display_options")
    if do:
        url_vars.append(("display_options", do))

    filename = "mobile_view.py" if html.mobile else "view.py"
    url_vars.insert(0, ("view_name", view_name))
    return filename + "?" + html.urlencode_vars(url_vars)


def get_tag_groups(row: Row, what: str) -> TagGroups:
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


def get_graph_timerange_from_painter_options() -> TimeRange:
    painter_options = PainterOptions.get_instance()
    value = painter_options.get("pnp_timerange")
    vs = painter_options.get_valuespec_of("pnp_timerange")
    assert isinstance(vs, valuespec.Timerange)
    start_time, end_time = vs.compute_range(value)[0]
    return int(start_time), int(end_time)


def paint_age(timestamp: Timestamp,
              has_been_checked: bool,
              bold_if_younger_than: int,
              mode: Optional[str] = None,
              what: str = 'past') -> CellSpec:
    if not has_been_checked:
        return "age", "-"

    painter_options = PainterOptions.get_instance()
    if mode is None:
        mode = painter_options.get("ts_format")

    if mode == "epoch":
        return "", str(int(timestamp))

    if mode == "both":
        css, h1 = paint_age(timestamp, has_been_checked, bold_if_younger_than, "abs", what=what)
        css, h2 = paint_age(timestamp, has_been_checked, bold_if_younger_than, "rel", what=what)
        return css, "%s - %s" % (h1, h2)

    dateformat = painter_options.get("ts_date")
    age = time.time() - timestamp
    if mode == "abs" or (mode == "mixed" and abs(age) >= 48 * 3600):
        return "age", time.strftime(dateformat + " %H:%M:%S", time.localtime(timestamp))

    warn_txt = u''
    output_format = u"%s"
    if what == 'future' and age > 0:
        warn_txt = ' <b>%s</b>' % _('in the past!')
    elif what == 'past' and age < 0:
        warn_txt = ' <b>%s</b>' % _('in the future!')
    elif what == 'both' and age > 0:
        output_format = "%%s %s" % _("ago")

    # Time delta less than two days => make relative time
    if age < 0:
        age = -age
        prefix = "in "
    else:
        prefix = ""
    if age < bold_if_younger_than:
        age_class = "age recent"
    else:
        age_class = "age"

    return age_class, prefix + (output_format % cmk.utils.render.approx_age(age)) + warn_txt


def paint_nagiosflag(row: Row, field: ColumnName, bold_if_nonzero: bool) -> CellSpec:
    nonzero = row[field] != 0
    return ("badflag" if nonzero == bold_if_nonzero else "goodflag",
            _("yes") if nonzero else _("no"))


def declare_simple_sorter(name: str, title: str, column: ColumnName, func: SorterFunction) -> None:
    register_sorter(name, {
        "title": title,
        "columns": [column],
        "cmp": lambda self, r1, r2: func(column, r1, r2)
    })


def declare_1to1_sorter(painter_name: PainterName,
                        func: SorterFunction,
                        col_num: int = 0,
                        reverse: bool = False) -> PainterName:
    painter = painter_registry[painter_name]()

    if not reverse:
        cmp_func = lambda self, r1, r2: func(painter.columns[col_num], r1, r2)
    else:
        cmp_func = lambda self, r1, r2: func(painter.columns[col_num], r2, r1)

    register_sorter(painter_name, {
        "title": painter.title,
        "columns": painter.columns,
        "cmp": cmp_func,
    })
    return painter_name


def cmp_simple_number(column: ColumnName, r1: Row, r2: Row) -> int:
    v1 = r1[column]
    v2 = r2[column]
    return (v1 > v2) - (v1 < v2)


def cmp_num_split(column: ColumnName, r1: Row, r2: Row) -> int:
    return cmk.gui.utils.cmp_num_split(r1[column].lower(), r2[column].lower())


def cmp_simple_string(column: ColumnName, r1: Row, r2: Row) -> int:
    v1, v2 = r1.get(column, ''), r2.get(column, '')
    return cmp_insensitive_string(v1, v2)


def cmp_insensitive_string(v1: str, v2: str) -> int:
    c = (v1.lower() > v2.lower()) - (v1.lower() < v2.lower())
    # force a strict order in case of equal spelling but different
    # case!
    if c == 0:
        return (v1 > v2) - (v1 < v2)
    return c


def cmp_string_list(column: ColumnName, r1: Row, r2: Row) -> int:
    v1 = ''.join(r1.get(column, []))
    v2 = ''.join(r2.get(column, []))
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
    return (get_custom_var(r1, key) > get_custom_var(r2, key)) - (get_custom_var(r1, key) <
                                                                  get_custom_var(r2, key))


def cmp_ip_address(column: ColumnName, r1: Row, r2: Row) -> int:
    def split_ip(ip):
        try:
            return tuple(int(part) for part in ip.split('.'))
        except Exception:
            return ip

    v1, v2 = split_ip(r1.get(column, '')), split_ip(r2.get(column, ''))
    return (v1 > v2) - (v1 < v2)


def get_custom_var(row: Row, key: str) -> str:
    return row["custom_variables"].get(key, "")


def get_perfdata_nth_value(row: Row, n: int, remove_unit: bool = False) -> str:
    perfdata = row.get("service_perf_data")
    if not perfdata:
        return ''
    try:
        parts = perfdata.split()
        if len(parts) <= n:
            return ""  # too few values in perfdata
        _varname, rest = parts[n].split("=")
        number = rest.split(';')[0]
        # Remove unit. Why should we? In case of sorter (numeric)
        if remove_unit:
            while len(number) > 0 and not number[-1].isdigit():
                number = number[:-1]
        return number
    except Exception as e:
        return str(e)


def _merge_data(data: List[LivestatusRow], columns: List[ColumnName]) -> List[LivestatusRow]:
    """Merge all data rows with different sites but the same value in merge_column

    We require that all column names are prefixed with the tablename. The column with the merge key
    is required to be the *second* column (right after the site column)"""
    merged: Dict[ColumnName, LivestatusRow] = {}

    # site column is not merged
    site_column_merge_func = lambda a, b: ""

    mergefuncs: List[Callable[[LivestatusColumn, LivestatusColumn],
                              LivestatusColumn]] = [site_column_merge_func]

    def worst_service_state(a, b):
        if a == 2 or b == 2:
            return 2
        return max(a, b)

    def worst_host_state(a, b):
        if a == 1 or b == 1:
            return 1
        return max(a, b)

    for c in columns:
        _tablename, col = c.split("_", 1)
        if col.startswith("num_") or col.startswith("members"):
            mergefunc = lambda a, b: a + b
        elif col.startswith("worst_service"):
            mergefunc = worst_service_state
        elif col.startswith("worst_host"):
            mergefunc = worst_host_state
        else:
            mergefunc = lambda a, b: a
        mergefuncs.append(mergefunc)

    for row in data:
        mergekey = row[1]
        if mergekey in merged:
            merged[mergekey] = cast(LivestatusRow,
                                    [f(a, b) for f, a, b in zip(mergefuncs, merged[mergekey], row)])
        else:
            merged[mergekey] = row

    # return all rows sorted according to merge key
    mergekeys = sorted(merged.keys())
    return [merged[k] for k in mergekeys]


def join_row(row: Row, cell: 'Cell') -> Row:
    if isinstance(cell, JoinCell):
        return row.get("JOIN", {}).get(cell.join_service())
    return row


def get_view_infos(view: ViewSpec) -> List[str]:
    """Return list of available datasources (used to render filters)"""
    ds_name = view.get('datasource', html.request.var('datasource'))
    return data_source_registry[ds_name]().infos


def replace_action_url_macros(url: str, what: str, row: Row) -> str:
    macros = {
        "HOSTNAME": row['host_name'],
        "HOSTADDRESS": row['host_address'],
        "USER_ID": config.user.id,
    }
    if what == 'service':
        macros.update({
            "SERVICEDESC": row['service_description'],
        })

    for key, val in macros.items():
        url = url.replace("$%s$" % key, val)
        url = url.replace("$%s_URL_ENCODED$" % key, html.urlencode(val))

    return url


def render_cache_info(what: str, row: Row) -> str:
    cached_at = row["service_cached_at"]
    cache_interval = row["service_cache_interval"]
    cache_age = time.time() - cached_at

    text = _("Cache generated %s ago, cache interval: %s") % \
            (cmk.utils.render.approx_age(cache_age), cmk.utils.render.approx_age(cache_interval))

    if cache_interval:
        percentage = 100.0 * cache_age / cache_interval
        text += _(", elapsed cache lifespan: %s") % cmk.utils.render.percent(percentage)

    return text


class ViewStore:
    @classmethod
    def get_instance(cls) -> 'ViewStore':
        """Use the request globals to prevent multiple instances during a request"""
        if 'view_store' not in g:
            g.view_store = cls()
        return g.view_store

    def __init__(self) -> None:
        self.all = self._load_all_views()
        self.permitted = self._load_permitted_views(self.all)

    def _load_all_views(self) -> AllViewSpecs:
        """Loads all view definitions from disk and returns them"""
        # Skip views which do not belong to known datasources
        views = visuals.load('views',
                             multisite_builtin_views,
                             skip_func=lambda v: v['datasource'] not in data_source_registry)
        views = _transform_old_views(views)
        return {viewname: transform_painter_spec(view) for viewname, view in views.items()}

    def _load_permitted_views(self, all_views: AllViewSpecs) -> PermittedViewSpecs:
        """Returns all view defitions that a user is allowed to use"""
        return visuals.available('views', all_views)


def get_all_views() -> AllViewSpecs:
    return ViewStore.get_instance().all


def get_permitted_views() -> PermittedViewSpecs:
    return ViewStore.get_instance().permitted


def transform_painter_spec(view: ViewSpec) -> ViewSpec:
    if 'painters' in view:
        view['painters'] = [PainterSpec(*v) for v in view['painters']]
    if 'group_painters' in view:
        view['group_painters'] = [PainterSpec(*v) for v in view['group_painters']]
    return view


# Convert views that are saved in the pre 1.2.6-style
# FIXME: Can be removed one day. Mark as incompatible change or similar.
def _transform_old_views(all_views: AllViewSpecs) -> AllViewSpecs:
    for view in all_views.values():
        ds_name = view['datasource']
        datasource = data_source_registry[ds_name]()

        if "context" not in view:  # legacy views did not have this explicitly
            view.setdefault("user_sortable", True)

        if 'context_type' in view:
            raise MKGeneralException(
                "Could not transform legacy view definition containing \"context_type\". "
                "You have to remove it or migrate it by hand")

        if 'single_infos' not in view:
            # This tries to map the datasource and additional settings of the
            # views to get the correct view context
            #
            # This code transforms views from views.mk (legacy format) to the current format
            try:
                hide_filters = view.get('hide_filters', [])

                if 'service' in hide_filters and 'host' in hide_filters:
                    view['single_infos'] = ['service', 'host']
                elif 'service' in hide_filters and 'host' not in hide_filters:
                    view['single_infos'] = ['service']
                elif 'host' in hide_filters:
                    view['single_infos'] = ['host']
                elif 'hostgroup' in hide_filters:
                    view['single_infos'] = ['hostgroup']
                elif 'servicegroup' in hide_filters:
                    view['single_infos'] = ['servicegroup']
                elif 'aggr_service' in hide_filters:
                    view['single_infos'] = ['service']
                elif 'aggr_name' in hide_filters:
                    view['single_infos'] = ['aggr']
                elif 'aggr_group' in hide_filters:
                    view['single_infos'] = ['aggr_group']
                elif 'log_contact_name' in hide_filters:
                    view['single_infos'] = ['contact']
                elif 'event_host' in hide_filters:
                    view['single_infos'] = ['host']
                elif hide_filters == ['event_id', 'history_line']:
                    view['single_infos'] = ['history']
                elif 'event_id' in hide_filters:
                    view['single_infos'] = ['event']
                elif 'aggr_hosts' in hide_filters:
                    view['single_infos'] = ['host']
                else:
                    # For all other context types assume the view is showing multiple objects
                    # and the datasource can simply be gathered from the datasource
                    view['single_infos'] = []
            except Exception:  # Exceptions can happen for views saved with certain GIT versions
                if config.debug:
                    raise

        # Convert from show_filters, hide_filters, hard_filters and hard_filtervars
        # to context construct
        if 'context' not in view:
            view[
                'show_filters'] = view['hide_filters'] + view['hard_filters'] + view['show_filters']

            single_keys = visuals.get_single_info_keys(view["single_infos"])

            # First get vars for the classic filters
            context: VisualContext = {}
            filtervars = dict(view['hard_filtervars'])
            all_vars = {}
            for filter_name in view['show_filters']:
                if filter_name in single_keys:
                    continue  # skip conflictings vars / filters

                filter_variables = context.setdefault(filter_name, {})
                assert isinstance(filter_variables, dict)

                try:
                    f = visuals.get_filter(filter_name)
                except Exception:
                    # The exact match filters have been removed. They where used only as
                    # link filters anyway - at least by the builtin views.
                    continue

                for var in f.htmlvars:
                    # Check whether or not the filter is supported by the datasource,
                    # then either skip or use the filter vars
                    if var in filtervars and f.info in datasource.infos:
                        value = filtervars[var]
                        all_vars[var] = value
                        filter_variables[var] = value

                # We changed different filters since the visuals-rewrite. This must be treated here, since
                # we need to transform views which have been created with the old filter var names.
                # Changes which have been made so far:
                changed_filter_vars = {
                    'serviceregex': {  # Name of the filter
                        # old var name: new var name
                        'service': 'service_regex',
                    },
                    'hostregex': {
                        'host': 'host_regex',
                    },
                    'hostgroupnameregex': {
                        'hostgroup_name': 'hostgroup_regex',
                    },
                    'servicegroupnameregex': {
                        'servicegroup_name': 'servicegroup_regex',
                    },
                    'opthostgroup': {
                        'opthostgroup': 'opthost_group',
                        'neg_opthostgroup': 'neg_opthost_group',
                    },
                    'optservicegroup': {
                        'optservicegroup': 'optservice_group',
                        'neg_optservicegroup': 'neg_optservice_group',
                    },
                    'hostgroup': {
                        'hostgroup': 'host_group',
                        'neg_hostgroup': 'neg_host_group',
                    },
                    'servicegroup': {
                        'servicegroup': 'service_group',
                        'neg_servicegroup': 'neg_service_group',
                    },
                    'host_contactgroup': {
                        'host_contactgroup': 'host_contact_group',
                        'neg_host_contactgroup': 'neg_host_contact_group',
                    },
                    'service_contactgroup': {
                        'service_contactgroup': 'service_contact_group',
                        'neg_service_contactgroup': 'neg_service_contact_group',
                    },
                }

                if filter_name in changed_filter_vars and f.info in datasource.infos:
                    for old_var, new_var in changed_filter_vars[filter_name].items():
                        if old_var in filtervars:
                            value = filtervars[old_var]
                            all_vars[new_var] = value
                            filter_variables[new_var] = value

            # Now, when there are single object infos specified, add these keys to the
            # context
            for single_key in single_keys:
                if single_key in all_vars:
                    context[single_key] = all_vars[single_key]

            view['context'] = context

        # Cleanup unused attributes
        for k in ['hide_filters', 'hard_filters', 'show_filters', 'hard_filtervars']:
            try:
                del view[k]
            except KeyError:
                pass

        visuals.transform_old_visual(view)

    return all_views


#.
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


def extract_painter_name(painter_spec: Union[PainterName, PainterSpec]) -> PainterName:
    if isinstance(painter_spec[0], tuple):
        return painter_spec[0][0]
    if isinstance(painter_spec, tuple):
        return painter_spec[0]
    if isinstance(painter_spec, str):
        return painter_spec


def painter_exists(painter_spec: PainterSpec) -> bool:
    painter_name = extract_painter_name(painter_spec)
    return painter_name in painter_registry


class Cell:
    """A cell is an instance of a painter in a view (-> a cell or a grouping cell)"""
    def __init__(self, view: 'View', painter_spec: Optional[PainterSpec] = None) -> None:
        self._view = view
        self._painter_name: Optional[PainterName] = None
        self._painter_params: Optional[PainterParameters] = None
        self._link_view_name: Optional[ViewName] = None
        self._tooltip_painter_name: Optional[PainterName] = None
        self._custom_title: Optional[str] = None

        if painter_spec:
            self._from_view(painter_spec)

    def _from_view(self, painter_spec: PainterSpec) -> None:
        self._painter_name = extract_painter_name(painter_spec)
        if isinstance(painter_spec[0], tuple):
            self._painter_params = painter_spec[0][1]
            self._custom_title = self._painter_params.get('column_title', None)

        self._link_view_name = painter_spec.link_view

        tooltip_painter_name = painter_spec.tooltip
        if tooltip_painter_name is not None and tooltip_painter_name in painter_registry:
            self._tooltip_painter_name = tooltip_painter_name

    def needed_columns(self) -> Set[ColumnName]:
        """Get a list of columns we need to fetch in order to render this cell"""

        columns = set(self.painter().columns)

        if self._link_view_name:
            if self._has_link():
                link_view = self._link_view()
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

    def join_service(self) -> Optional[ServiceName]:
        return None

    def _has_link(self) -> bool:
        return self._link_view_name is not None

    def _link_view(self) -> Optional[ViewSpec]:
        if self._link_view_name is None:
            return None

        try:
            return get_permitted_views()[self._link_view_name]
        except KeyError:
            return None

    def painter(self) -> Painter:
        return painter_registry[self.painter_name()]()

    def painter_name(self) -> PainterName:
        assert self._painter_name is not None
        return self._painter_name

    def export_title(self) -> str:
        return ensure_str(self.painter_name())

    def painter_options(self) -> List[str]:
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
    def printable(self) -> Union[bool, str]:
        return self.painter().printable

    def has_tooltip(self) -> bool:
        return self._tooltip_painter_name is not None

    def tooltip_painter_name(self) -> str:
        assert self._tooltip_painter_name is not None
        return self._tooltip_painter_name

    def tooltip_painter(self) -> Painter:
        assert self._tooltip_painter_name is not None
        return painter_registry[self._tooltip_painter_name]()

    def paint_as_header(self, is_last_column_header: bool = False) -> None:
        # Optional: Sort link in title cell
        # Use explicit defined sorter or implicit the sorter with the painter name
        # Important for links:
        # - Add the display options (Keeping the same display options as current)
        # - Link to _self (Always link to the current frame)
        classes: List[str] = []
        onclick = ''
        title = u''
        if display_options.enabled(display_options.L) \
           and self._view.spec.get('user_sortable', False) \
           and _get_sorter_name_of_painter(self.painter_name()) is not None:
            params: HTTPVariables = [
                ('sort', self._sort_url()),
            ]
            if display_options.title_options:
                params.append(('display_options', display_options.title_options))

            classes += ["sort"]
            onclick = "location.href=\'%s\'" % makeuri(
                request, addvars=params, remove_prefix='sort')
            title = _('Sort by %s') % self.title()

        if is_last_column_header:
            classes.append("last_col")

        html.open_th(class_=classes, onclick=onclick, title=title)
        html.write(self.title())
        html.close_th()

    def _sort_url(self) -> str:
        """
        The following sorters need to be handled in this order:

        1. group by sorter (needed in grouped views)
        2. user defined sorters (url sorter)
        3. configured view sorters
        """
        sorter = []

        group_sort, user_sort, view_sort = _get_separated_sorters(self._view)

        sorter = group_sort + user_sort + view_sort

        # Now apply the sorter of the current column:
        # - Negate/Disable when at first position
        # - Move to the first position when already in sorters
        # - Add in the front of the user sorters when not set
        painter_name = self.painter_name()
        sorter_name = _get_sorter_name_of_painter(painter_name)
        if sorter_name is None:
            # Do not change anything in case there is no sorter for the current column
            sorters = [SorterSpec(*s) for s in sorter]
            return _encode_sorter_url(sorters)

        if painter_name in ['svc_metrics_hist', 'svc_metrics_forecast']:
            uuid = ':%s' % self.painter_parameters()['uuid']
            assert sorter_name is not None
            sorter_name += uuid

        this_asc_sorter = SorterSpec(sorter_name, False, self.join_service())
        this_desc_sorter = SorterSpec(sorter_name, True, self.join_service())

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

        sorters = [SorterSpec(*s) for s in sorter]
        return _encode_sorter_url(sorters)

    def render(self, row: Row) -> CellSpec:
        row = join_row(row, self)

        try:
            tdclass, content = self.render_content(row)
        except Exception:
            logger.exception("Failed to render painter '%s' (Row: %r)", self._painter_name, row)
            raise

        if tdclass is None:
            tdclass = ""

        if tdclass == "" and content == "":
            return "", ""

        # Add the optional link to another view
        if content and self._has_link() and self._link_view_name is not None:
            content = link_to_view(content, row, self._link_view_name)

        # Add the optional mouseover tooltip
        if content and self.has_tooltip():
            tooltip_cell = Cell(self._view, PainterSpec(self.tooltip_painter_name()))
            _tooltip_tdclass, tooltip_content = tooltip_cell.render_content(row)
            assert not isinstance(tooltip_content, dict)
            tooltip_text = escaping.strip_tags(tooltip_content)
            if tooltip_text:
                content = '<span title="%s">%s</span>' % (tooltip_text, content)

        return tdclass, content

    # Same as self.render() for HTML output: Gets a painter and a data
    # row and creates the text for being painted.
    def render_for_pdf(self, row: Row, time_range: TimeRange) -> PDFCellSpec:
        # TODO: Move this somewhere else!
        def find_htdocs_image_path(filename):
            for file_path in [
                    cmk.utils.paths.local_web_dir / "htdocs" / filename,
                    Path(cmk.utils.paths.web_dir, "htdocs", filename),
            ]:
                if file_path.exists():
                    return str(file_path)

        try:
            row = join_row(row, self)
            css_classes, rendered_txt = self.render_content(row)
            if rendered_txt is None:
                return css_classes, ""
            assert not isinstance(rendered_txt, dict)

            txt: PDFCellContent = rendered_txt.strip()

            # Handle <img...>. Our PDF writer cannot draw arbitrary
            # images, but all that we need for showing simple icons.
            # Current limitation: *one* image
            assert not isinstance(txt, tuple)
            if txt.lower().startswith("<img"):
                img_filename = re.sub('.*src=["\']([^\'"]*)["\'].*', "\\1", str(txt))
                img_path = find_htdocs_image_path(img_filename)
                if img_path:
                    txt = ("icon", img_path)
                else:
                    txt = img_filename

            if isinstance(txt, HTML):
                txt = escaping.strip_tags("%s" % txt)

            elif not isinstance(txt, tuple):
                txt = escaping.unescape_attributes(txt)
                txt = escaping.strip_tags(txt)

            return css_classes, txt
        except Exception:
            raise MKGeneralException('Failed to paint "%s": %s' %
                                     (self.painter_name(), traceback.format_exc()))

    # TODO: We really should have some intermediate "data" layer that would make it possible to
    # extract the data for the export in a cleaner way.
    def render_for_export(self, row):
        rendered_txt = self.render_content(row)[1]
        if rendered_txt is None:
            return ""

        # The aggr_treestate painters are returning a dictionary data structure
        # (see paint_aggregated_tree_state()) in case the output_format is not
        # HTML. Hand over the whole data structure to the caller. It will be
        # converted to str during rendering.
        if isinstance(rendered_txt, dict):
            return rendered_txt

        txt: str = rendered_txt.strip()

        # Similar to the PDF rendering hack above, but this time we extract the title from our icons
        # and add them to the CSV export instead of stripping the whole HTML tag.
        # Current limitation: *one* image
        assert not isinstance(txt, tuple)
        if txt.lower().startswith("<img"):
            txt = re.sub('.*title=["\']([^\'"]*)["\'].*', "\\1", str(txt))
        return txt

    def render_content(self, row: Row) -> CellSpec:
        if not row:
            return "", ""  # nothing to paint

        painter = self.painter()
        result = painter.render(row, self)
        if not isinstance(result, tuple) or len(result) != 2:
            raise Exception(_("Painter %r returned invalid result: %r") % (painter.ident, result))
        return result

    def paint(self, row: Row, tdattrs: str = "", is_last_cell: bool = False) -> bool:
        tdclass, content = self.render(row)
        has_content = content != ""
        assert not isinstance(content, dict)

        if is_last_cell:
            if tdclass is None:
                tdclass = "last_col"
            else:
                tdclass += " last_col"

        if tdclass:
            html.write("<td %s class=\"%s\">" % (tdattrs, tdclass))
            html.write(content)
            html.close_td()
        else:
            html.write("<td %s>" % (tdattrs))
            html.write(content)
            html.close_td()

        return has_content


SorterSpec = NamedTuple("SorterSpec", [
    ("sorter", SorterName),
    ("negate", bool),
    ("join_key", Optional[str]),
])
# Is used to add default arguments to the named tuple. Would be nice to have a cleaner solution
SorterSpec.__new__.__defaults__ = (None,) * len(SorterSpec._fields)  # type: ignore[attr-defined]

SorterEntry = NamedTuple("SorterEntry", [
    ("sorter", Sorter),
    ("negate", bool),
    ("join_key", Optional[str]),
])
# Is used to add default arguments to the named tuple. Would be nice to have a cleaner solution
SorterEntry.__new__.__defaults__ = (None,) * len(SorterEntry._fields)  # type: ignore[attr-defined]


def _encode_sorter_url(sorters: List[SorterSpec]) -> str:
    p = []
    for s in sorters:
        url = (u'-' if s.negate else u'') + s.sorter
        if s.join_key:
            url += '~' + s.join_key
        p.append(url)

    return ensure_str(','.join(p))


def _parse_url_sorters(sort: Optional[str]) -> List[SorterSpec]:
    sorters: List[SorterSpec] = []
    if not sort:
        return sorters
    for s in sort.split(','):
        if "~" in s:
            sorter, join_index = s.split('~', 1)  # type: Tuple[SorterName, Optional[str]]
        else:
            sorter, join_index = s, None

        negate = False
        if sorter.startswith('-'):
            negate = True
            sorter = sorter[1:]

        sorters.append(SorterSpec(sorter, negate, join_index))
    return sorters


class JoinCell(Cell):
    def __init__(self, view: 'View', painter_spec: PainterSpec) -> None:
        self._join_service_descr: Optional[ServiceName] = None
        super(JoinCell, self).__init__(view, painter_spec)

    def _from_view(self, painter_spec: PainterSpec) -> None:
        super(JoinCell, self)._from_view(painter_spec)

        self._join_service_descr = painter_spec.join_index

        if painter_spec.column_title and self._custom_title is None:
            self._custom_title = painter_spec.column_title

    def is_joined(self) -> bool:
        return True

    def join_service(self) -> ServiceName:
        assert self._join_service_descr is not None
        return self._join_service_descr

    def livestatus_filter(self, join_column_name: str) -> LivestatusQuery:
        return "Filter: %s = %s" % \
            (livestatus.lqencode(join_column_name), livestatus.lqencode(self.join_service()))

    def title(self, use_short: bool = True) -> str:
        return self._custom_title or self.join_service()

    def export_title(self) -> str:
        return "%s.%s" % (self._painter_name, self.join_service())


class EmptyCell(Cell):
    def render(self, row):
        return "", ""

    def paint(self, row, tdattrs="", is_last_cell=False):
        return False


def output_csv_headers(view: ViewSpec) -> None:
    filename = '%s-%s.csv' % (view['name'],
                              time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time())))
    html.response.headers["Content-Disposition"] = "Attachment; filename=\"%s\"" % ensure_str(
        filename)


def _get_sorter_name_of_painter(
        painter_name_or_spec: Union[PainterName, PainterSpec]) -> Optional[SorterName]:
    painter_name = extract_painter_name(painter_name_or_spec)
    painter = painter_registry[painter_name]()
    if painter.sorter:
        return painter.sorter

    if painter_name in sorter_registry:
        return painter_name

    return None


def _get_separated_sorters(
        view: 'View') -> Tuple[List[SorterSpec], List[SorterSpec], List[SorterSpec]]:
    group_sort = _get_group_sorters(view)
    view_sort = [SorterSpec(*s) for s in view.spec['sorters'] if not s[0] in group_sort]
    user_sort = view.user_sorters or []

    _substract_sorters(user_sort, group_sort)
    _substract_sorters(view_sort, user_sort)

    return group_sort, user_sort, view_sort


def _get_group_sorters(view: 'View') -> List[SorterSpec]:
    group_sort: List[SorterSpec] = []
    for p in view.spec['group_painters']:
        if not painter_exists(p):
            continue
        sorter_name = _get_sorter_name_of_painter(p)
        if sorter_name is None:
            continue

        group_sort.append(SorterSpec(sorter_name, False, None))
    return group_sort


def _substract_sorters(base: List[SorterSpec], remove: List[SorterSpec]) -> None:
    for s in remove:
        negated_sorter = SorterSpec(s[0], not s[1], None)

        if s in base:
            base.remove(s)
        elif negated_sorter in base:
            base.remove(negated_sorter)


def make_service_breadcrumb(host_name: HostName, service_name: ServiceName) -> Breadcrumb:
    permitted_views = get_permitted_views()
    service_view_spec = permitted_views["service"]

    breadcrumb = make_host_breadcrumb(host_name)

    # Add service home page
    breadcrumb.append(
        BreadcrumbItem(
            title=view_title(service_view_spec),
            url=makeuri_contextless(
                request,
                [("view_name", "service"), ("host", host_name), ("service", service_name)],
                filename="view.py",
            ),
        ))

    return breadcrumb


def make_host_breadcrumb(host_name: HostName) -> Breadcrumb:
    """Create the breadcrumb down to the "host home page" level"""
    permitted_views = get_permitted_views()
    allhosts_view_spec = permitted_views["allhosts"]

    breadcrumb = make_topic_breadcrumb(mega_menu_registry.menu_monitoring(),
                                       PagetypeTopics.get_topic(allhosts_view_spec["topic"]))

    # 1. level: list of all hosts
    breadcrumb.append(
        BreadcrumbItem(
            title=_u(allhosts_view_spec["title"]),
            url=makeuri_contextless(
                request,
                [("view_name", "allhosts")],
                filename="view.py",
            ),
        ))

    # 2. level: host home page
    host_view_spec = permitted_views["host"]
    breadcrumb.append(
        BreadcrumbItem(
            title=view_title(host_view_spec),
            url=makeuri_contextless(
                request,
                [("view_name", "host"), ("host", host_name)],
                filename="view.py",
            ),
        ))

    return breadcrumb
