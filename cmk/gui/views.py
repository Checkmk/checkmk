#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import ast
import time
import pprint
import traceback
import json
import functools
from typing import (Any, Callable, Dict, List, Optional, Sequence, Set, Tuple as _Tuple, Union,
                    Iterator, Type)

import livestatus
from livestatus import SiteId

import cmk.utils.version as cmk_version
import cmk.utils.paths
from cmk.utils.structured_data import StructuredDataTree
from cmk.utils.prediction import livestatus_lql

import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.weblib as weblib
import cmk.gui.forms as forms
import cmk.gui.inventory as inventory
import cmk.gui.visuals as visuals
import cmk.gui.sites as sites
import cmk.gui.pagetypes as pagetypes
import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.view_utils
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.breadcrumb import make_topic_breadcrumb, Breadcrumb, BreadcrumbItem
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    PageMenuPopup,
    PageMenuSidePopup,
    make_display_options_dropdown,
    make_simple_link,
    make_checkbox_selection_topic,
    toggle_page_menu_entries,
    make_simple_form_page_menu,
)
from cmk.gui.display_options import display_options
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    CascadingDropdownChoice,
    Dictionary,
    DropdownChoice,
    DropdownChoiceEntry,
    FixedValue,
    Hostname,
    IconSelector,
    Integer,
    ListChoice,
    ListOf,
    TextUnicode,
    Transform,
    Tuple,
    ValueSpec,
)
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html, g, request as global_request
from cmk.gui.exceptions import (
    HTTPRedirect,
    MKGeneralException,
    MKUserError,
    MKInternalError,
)
from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
    declare_permission,
)
from cmk.gui.plugins.visuals.utils import (
    visual_info_registry,
    VisualInfo,
    visual_type_registry,
    VisualType,
    Filter,
)
from cmk.gui.plugins.views.icons.utils import (
    icon_and_action_registry,
    Icon,
)
from cmk.gui.plugins.views.utils import (
    command_registry,
    CommandGroup,
    Command,
    layout_registry,
    exporter_registry,
    data_source_registry,
    painter_registry,
    Painter,
    sorter_registry,
    get_permitted_views,
    get_all_views,
    painter_exists,
    PainterOptions,
    get_tag_groups,
    _parse_url_sorters,
    SorterEntry,
    make_host_breadcrumb,
    make_service_breadcrumb,
    SorterSpec,
    Sorter,
    DerivedColumnsSorter,
)

# Needed for legacy (pre 1.6) plugins
from cmk.gui.htmllib import HTML  # noqa: F401 # pylint: disable=unused-import
from cmk.gui.plugins.views.utils import (  # noqa: F401 # pylint: disable=unused-import
    view_title, multisite_builtin_views, view_hooks, inventory_displayhints, register_command_group,
    transform_action_url, is_stale, paint_stalified, paint_host_list, format_plugin_output,
    link_to_view, url_to_view, row_id, group_value, view_is_enabled, paint_age, declare_1to1_sorter,
    declare_simple_sorter, cmp_simple_number, cmp_simple_string, cmp_insensitive_string,
    cmp_num_split, cmp_custom_variable, cmp_service_name_equiv, cmp_string_list, cmp_ip_address,
    get_custom_var, get_perfdata_nth_value, join_row, get_view_infos, replace_action_url_macros,
    Cell, JoinCell, register_legacy_command, register_painter, register_sorter, ABCDataSource,
    Layout,
)

# Needed for legacy (pre 1.6) plugins
from cmk.gui.plugins.views.icons import (  # noqa: F401  # pylint: disable=unused-import
    multisite_icons_and_actions, get_multisite_icons, get_icons, iconpainter_columns,
)

import cmk.gui.plugins.views.inventory
import cmk.gui.plugins.views.availability
from cmk.gui.plugins.views.perfometers import perfometers  # noqa: F401 # pylint: disable=unused-import

if not cmk_version.is_raw_edition():
    import cmk.gui.cee.plugins.views  # pylint: disable=no-name-in-module
    import cmk.gui.cee.plugins.views.icons  # pylint: disable=no-name-in-module

if cmk_version.is_managed_edition():
    import cmk.gui.cme.plugins.views  # pylint: disable=no-name-in-module

from cmk.gui.type_defs import (PainterSpec, HTTPVariables, InfoName, FilterHeaders, Row, Rows,
                               ColumnName, Visual, ViewSpec)

from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.utils.confirm_with_preview import confirm_with_preview

# Datastructures and functions needed before plugins can be loaded
loaded_with_language: Union[bool, None, str] = False

# TODO: Kept for compatibility with pre 1.6 plugins. Plugins will not be used anymore, but an error
# will be displayed.
multisite_painter_options: Dict[str, Any] = {}
multisite_layouts: Dict[str, Any] = {}
multisite_commands: List[Dict[str, Any]] = []
multisite_datasources: Dict[str, Any] = {}
multisite_painters: Dict[str, Dict[str, Any]] = {}
multisite_sorters: Dict[str, Any] = {}


@visual_type_registry.register
class VisualTypeViews(VisualType):
    """Register the views as a visual type"""
    @property
    def ident(self):
        return "views"

    @property
    def title(self):
        return _("view")

    @property
    def plural_title(self):
        return _("views")

    @property
    def ident_attr(self):
        return "view_name"

    @property
    def multicontext_links(self):
        return False

    @property
    def show_url(self):
        return "view.py"

    def page_menu_add_to_entries(self, add_type: str) -> Iterator[PageMenuEntry]:
        return iter(())

    def add_visual_handler(self, target_visual_name, add_type, context, parameters):
        return None

    def load_handler(self):
        pass

    @property
    def permitted_visuals(self):
        return get_permitted_views()

    def link_from(self, linking_view, linking_view_rows, visual, context_vars):
        """This has been implemented for HW/SW inventory views which are often useless when a host
        has no such information available. For example the "Oracle Tablespaces" inventory view is
        useless on hosts that don't host Oracle databases."""
        result = super(VisualTypeViews, self).link_from(linking_view, linking_view_rows, visual,
                                                        context_vars)
        if result is False:
            return False

        link_from = visual["link_from"]
        if not link_from:
            return True  # No link from filtering: Always display this.

        inventory_tree_condition = link_from.get("has_inventory_tree")
        if inventory_tree_condition and not _has_inventory_tree(
                linking_view, linking_view_rows, visual, context_vars, inventory_tree_condition):
            return False

        inventory_tree_history_condition = link_from.get("has_inventory_tree_history")
        if inventory_tree_history_condition and not _has_inventory_tree(
                linking_view,
                linking_view_rows,
                visual,
                context_vars,
                inventory_tree_history_condition,
                is_history=True):
            return False

        return True


def _has_inventory_tree(linking_view, rows, view, context_vars, invpath, is_history=False):
    context = dict(context_vars)
    hostname = context.get("host")
    if hostname is None:
        return True  # No host data? Keep old behaviour

    if hostname == "":
        return False

    # TODO: host is not correctly validated by visuals. Do it here for the moment.
    try:
        Hostname().validate_value(hostname, None)
    except MKUserError:
        return False

    # FIXME In order to decide whether this view is enabled
    # do we really need to load the whole tree?
    try:
        struct_tree = _get_struct_tree(is_history, hostname, context.get("site"))
    except inventory.LoadStructuredDataError:
        return False

    if not struct_tree:
        return False

    if struct_tree.is_empty():
        return False

    if isinstance(invpath, list):
        # For plugins/views/inventory.py:RowMultiTableInventory we've to check
        # if a given host has inventory data below several inventory paths
        return any(_has_children(struct_tree, ipath) for ipath in invpath)
    return _has_children(struct_tree, invpath)


def _has_children(struct_tree, invpath):
    parsed_path, _attribute_keys = inventory.parse_tree_path(invpath)
    if parsed_path:
        children = struct_tree.get_sub_children(parsed_path)
    else:
        children = [struct_tree.get_root_container()]
    if children is None:
        return False
    return True


def _get_struct_tree(is_history, hostname, site_id):
    struct_tree_cache = g.setdefault("struct_tree_cache", {})
    cache_id = (is_history, hostname, site_id)
    if cache_id in struct_tree_cache:
        return struct_tree_cache[cache_id]

    if is_history:
        struct_tree = inventory.load_filtered_inventory_tree(hostname)
    else:
        row = inventory.get_status_data_via_livestatus(site_id, hostname)
        struct_tree = inventory.load_filtered_and_merged_tree(row)

    struct_tree_cache[cache_id] = struct_tree
    return struct_tree


@permission_section_registry.register
class PermissionSectionViews(PermissionSection):
    @property
    def name(self):
        return "view"

    @property
    def title(self):
        return _("Views")

    @property
    def do_sort(self):
        return True


class View:
    """Manages processing of a single view, e.g. during rendering"""
    def __init__(self, view_name: str, view_spec: Dict, context: Dict) -> None:
        super(View, self).__init__()
        self.name = view_name
        self.spec = view_spec
        self.context = context
        self._row_limit: Optional[int] = None
        self._only_sites: Optional[List[SiteId]] = None
        self._user_sorters: Optional[List[SorterSpec]] = None
        self._want_checkboxes: bool = False

    @property
    def datasource(self) -> ABCDataSource:
        try:
            return data_source_registry[self.spec["datasource"]]()
        except KeyError:
            if self.spec["datasource"].startswith("mkeventd_"):
                raise MKUserError(
                    None,
                    _("The Event Console view '%s' can not be rendered. The Event Console is possibly "
                      "disabled.") % self.name)
            raise MKUserError(
                None,
                _("The view '%s' using the datasource '%s' can not be rendered "
                  "because the datasource does not exist.") % (self.name, self.datasource))

    @property
    def row_cells(self) -> List[Cell]:
        """Regular cells are displaying information about the rows of the type the view is about"""
        cells: List[Cell] = []
        for e in self.spec["painters"]:
            if not painter_exists(e):
                continue

            if e.join_index is not None:
                cells.append(JoinCell(self, e))
            else:
                cells.append(Cell(self, e))

        return cells

    @property
    def group_cells(self) -> List[Cell]:
        """Group cells are displayed as titles of grouped rows"""
        return [Cell(self, e) for e in self.spec["group_painters"] if painter_exists(e)]

    @property
    def join_cells(self) -> List[JoinCell]:
        """Join cells are displaying information of a joined source (e.g.service data on host views)"""
        return [x for x in self.row_cells if isinstance(x, JoinCell)]

    @property
    def sorters(self) -> List[SorterEntry]:
        """Returns the list of effective sorters to be used to sort the rows of this view"""
        return self._get_sorter_entries(
            self.user_sorters if self.user_sorters else self.spec["sorters"])

    # TODO: Improve argument type
    def _get_sorter_entries(self, sorter_list: List) -> List[SorterEntry]:
        sorters = []
        for entry in sorter_list:
            if not isinstance(entry, SorterEntry):
                entry = SorterEntry(*entry)

            sorter_name = entry.sorter
            uuid = None
            if ":" in entry.sorter:
                sorter_name, uuid = entry.sorter.split(':', 1)

            sorter = sorter_registry.get(sorter_name, None)

            if sorter is None:
                continue  # Skip removed sorters

            sorter_instance = sorter()
            if isinstance(sorter_instance, DerivedColumnsSorter):
                sorter_instance.derived_columns(self, uuid)

            sorters.append(
                SorterEntry(sorter=sorter_instance, negate=entry.negate, join_key=entry.join_key))
        return sorters

    @property
    def row_limit(self) -> Optional[int]:
        if self.datasource.ignore_limit:
            return None

        return self._row_limit

    @row_limit.setter
    def row_limit(self, row_limit: Optional[int]) -> None:
        self._row_limit = row_limit

    @property
    def only_sites(self) -> Optional[List[SiteId]]:
        """Optional list of sites to query instead of all sites

        This is a performance feature. It is highly recommended to set the only_sites attribute
        whenever it is possible. In the moment it is set a livestatus query is not sent to all
        sites anymore but only to the given list of sites."""
        return self._only_sites

    @only_sites.setter
    def only_sites(self, only_sites: Optional[List[SiteId]]) -> None:
        self._only_sites = only_sites

    @property
    def layout(self) -> Layout:
        """Return the HTML layout of the view"""
        if "layout" in self.spec:
            return layout_registry[self.spec["layout"]]()

        raise MKUserError(
            None,
            _("The view '%s' using the layout '%s' can not be rendered "
              "because the layout does not exist.") % (self.name, self.spec.get("layout")))

    @property
    def user_sorters(self) -> Optional[List[SorterSpec]]:
        """Optional list of sorters to use for rendering the view

        The user may click on the headers of tables to change the default view sorting. In the
        moment the user overrides the sorting configured for the view in self.spec"""
        # TODO: Only process in case the view is user sortable
        return self._user_sorters

    @user_sorters.setter
    def user_sorters(self, user_sorters: Optional[List[SorterSpec]]) -> None:
        self._user_sorters = user_sorters

    @property
    def want_checkboxes(self) -> bool:
        """Whether or not the user that displays this view requests to show the checkboxes"""
        return self._want_checkboxes

    @want_checkboxes.setter
    def want_checkboxes(self, want_checkboxes: bool) -> None:
        self._want_checkboxes = want_checkboxes

    @property
    def checkboxes_enforced(self) -> bool:
        """Whether or not the view is configured to always show checkboxes"""
        return self.spec.get("force_checkboxes", False)

    @property
    def checkboxes_displayed(self) -> bool:
        """Whether or not to display the checkboxes in the current view"""
        return self.layout.can_display_checkboxes and (self.checkboxes_enforced or
                                                       self.want_checkboxes)

    def breadcrumb(self) -> Breadcrumb:
        """Render the breadcrumb for the current view

        In case of views we not only have a hierarchy of

        1. main menu
        2. main menu topic

        We also have a hierarchy between some of the views (see _host_hierarchy_breadcrumb).  But
        this is not the case for all views. A lot of the views are direct children of the topic
        level.
        """

        # View without special hierarchy
        if "host" not in self.spec['single_infos']:
            request_vars: HTTPVariables = [("view_name", self.name)]
            request_vars += list(
                visuals.get_singlecontext_html_vars(self.context,
                                                    self.spec["single_infos"]).items())

            breadcrumb = make_topic_breadcrumb(
                mega_menu_registry.menu_monitoring(),
                pagetypes.PagetypeTopics.get_topic(self.spec["topic"]))
            breadcrumb.append(
                BreadcrumbItem(
                    title=view_title(self.spec),
                    url=makeuri_contextless(global_request, request_vars),
                ))
            return breadcrumb

        # Now handle the views within the host view hierarchy
        return self._host_hierarchy_breadcrumb()

    def _host_hierarchy_breadcrumb(self) -> Breadcrumb:
        """Realize the host hierarchy breadcrumb

        All hosts
         |
         + host home view
           |
           + host views
           |
           + service home view
             |
             + service views
        """
        host_name = self.context["host"]
        breadcrumb = make_host_breadcrumb(host_name)

        if self.name == "host":
            # In case we are on the host homepage, we have the final breadcrumb
            return breadcrumb

        # 3a) level: other single host pages
        if "service" not in self.spec['single_infos']:
            # All other single host pages are right below the host home page
            breadcrumb.append(
                BreadcrumbItem(
                    title=view_title(self.spec),
                    url=makeuri_contextless(
                        global_request,
                        [("view_name", self.name), ("host", host_name)],
                    ),
                ))
            return breadcrumb

        breadcrumb = make_service_breadcrumb(host_name, self.context["service"])

        if self.name == "service":
            # In case we are on the service home page, we have the final breadcrumb
            return breadcrumb

        # All other single service pages are right below the host home page
        breadcrumb.append(
            BreadcrumbItem(
                title=view_title(self.spec),
                url=makeuri_contextless(
                    global_request,
                    [
                        ("view_name", self.name),
                        ("host", host_name),
                        ("service", self.context["service"]),
                    ],
                ),
            ))

        return breadcrumb


class ABCViewRenderer(metaclass=abc.ABCMeta):
    def __init__(self, view: View) -> None:
        super().__init__()
        self.view = view

    @abc.abstractmethod
    def render(self, rows, group_cells, cells, show_checkboxes, num_columns, show_filters,
               unfiltered_amount_of_rows):
        raise NotImplementedError()


class GUIViewRenderer(ABCViewRenderer):
    def __init__(self, view: View, show_buttons: bool) -> None:
        super(GUIViewRenderer, self).__init__(view)
        self._show_buttons = show_buttons

    def render(self, rows, group_cells, cells, show_checkboxes, num_columns, show_filters,
               unfiltered_amount_of_rows):
        view_spec = self.view.spec

        if html.transaction_valid() and html.do_actions():
            html.set_browser_reload(0)

        # Show/Hide the header with page title, MK logo, etc.
        if display_options.enabled(display_options.H):
            html.body_start(view_title(view_spec))

        if display_options.enabled(display_options.T):
            breadcrumb = self.view.breadcrumb()
            html.top_heading(view_title(view_spec),
                             breadcrumb,
                             page_menu=self._page_menu(breadcrumb, rows, show_filters))
            html.begin_page_content()

        has_done_actions = False
        row_count = len(rows)

        command_form = _should_show_command_form(self.view.datasource)
        if command_form:
            weblib.init_selection()

        # Used this before. This does not looked like it's correct, replaced the logic
        #enable_commands = painter_options.painter_option_form_enabled()
        #enable_checkboxes = view.layout.can_display_checkboxes and not checkboxes_enforced
        #selection_enabled = enable_checkboxes if enable_commands else checkboxes_enforced
        html.javascript('cmk.selection.set_selection_enabled(%s);' %
                        json.dumps(self.view.checkboxes_displayed))

        layout = self.view.layout

        # Display the filter form on page rendering in some cases
        if self._should_show_filter_form(view_spec):
            html.final_javascript("cmk.page_menu.open_popup('popup_filters');")

        # Actions
        if command_form:
            # There are one shot actions which only want to affect one row, filter the rows
            # by this id during actions
            if html.request.has_var("_row_id") and html.do_actions():
                rows = filter_selected_rows(view_spec, rows, [html.request.has_var("_row_id")])

            # If we are currently within an action (confirming or executing), then
            # we display only the selected rows (if checkbox mode is active)
            elif show_checkboxes and html.do_actions():
                rows = filter_selected_rows(
                    view_spec, rows,
                    config.user.get_rowselection(weblib.selection_id(),
                                                 'view-' + view_spec['name']))

            if html.do_actions() and html.transaction_valid():  # submit button pressed, no reload
                try:
                    # Create URI with all actions variables removed
                    backurl = makeuri(global_request, [], delvars=['filled_in', 'actions'])
                    has_done_actions = do_actions(view_spec, self.view.datasource.infos[0], rows,
                                                  backurl)
                except MKUserError as e:
                    html.show_error("%s" % e)
                    html.add_user_error(e.varname, e)

        # Also execute commands in cases without command form (needed for Python-
        # web service e.g. for NagStaMon)
        elif row_count > 0 and config.user.may("general.act") \
             and html.do_actions() and html.transaction_valid():

            # There are one shot actions which only want to affect one row, filter the rows
            # by this id during actions
            if html.request.has_var("_row_id") and html.do_actions():
                rows = filter_selected_rows(view_spec, rows, [html.request.has_var("_row_id")])

            try:
                do_actions(view_spec, self.view.datasource.infos[0], rows, '')
            except Exception:
                pass  # currently no feed back on webservice

        # The refreshing content container
        if display_options.enabled(display_options.R):
            html.open_div(id_="data_container")

        if not has_done_actions:
            if display_options.enabled(display_options.W):
                if cmk.gui.view_utils.row_limit_exceeded(unfiltered_amount_of_rows,
                                                         self.view.row_limit):
                    cmk.gui.view_utils.query_limit_exceeded_warn(self.view.row_limit, config.user)
                    del rows[self.view.row_limit:]
            layout.render(rows, view_spec, group_cells, cells, num_columns, show_checkboxes and
                          not html.do_actions())
            headinfo = "%d %s" % (row_count, _("row") if row_count == 1 else _("rows"))
            if show_checkboxes:
                selected = filter_selected_rows(
                    view_spec, rows,
                    config.user.get_rowselection(weblib.selection_id(),
                                                 'view-' + view_spec['name']))
                headinfo = "%d/%s" % (len(selected), headinfo)

            html.javascript("cmk.utils.update_header_info(%s);" % json.dumps(headinfo))

            # The number of rows might have changed to enable/disable actions and checkboxes
            if self._show_buttons:
                # don't take display_options into account here ('c' is set during reload)
                toggle_page_menu_entries(
                    css_class="command",
                    state=row_count > 0 and
                    _should_show_command_form(self.view.datasource, ignore_display_option=True))

            # Play alarm sounds, if critical events have been displayed
            if display_options.enabled(display_options.S) and view_spec.get("play_sounds"):
                play_alarm_sounds()
        else:
            # Always hide action related context links in this situation
            toggle_page_menu_entries(css_class="command", state=False)

        # In multi site setups error messages of single sites do not block the
        # output and raise now exception. We simply print error messages here.
        # In case of the web service we show errors only on single site installations.
        if config.show_livestatus_errors and display_options.enabled(display_options.W):
            for info in sites.live().dead_sites().values():
                if isinstance(info["site"], dict):
                    html.show_error(
                        "<b>%s - %s</b><br>%s" %
                        (info["site"]["alias"], _('Livestatus error'), info["exception"]))

        if display_options.enabled(display_options.R):
            html.close_div()

        if display_options.enabled(display_options.T):
            html.end_page_content()
        html.bottom_focuscode()
        if display_options.enabled(display_options.Z):
            html.bottom_footer()

        if display_options.enabled(display_options.H):
            html.body_end()

    def _should_show_filter_form(self, view_spec: ViewSpec) -> bool:
        """Whether or not the filter form should be displayed on page load

        a) In case the user toggled the popup in the frontend, always enforce that property

        b) Show in case the view is a "mustsearch" view (User needs to submit the filter form before
        data is shown).

        c) Show after submitting the filter form. The user probably wants to update the filters
        after first filtering.
        """
        show_form = html.request.get_integer_input("_show_filter_form")
        if show_form is not None:
            return show_form == 1

        if view_spec.get("mustsearch"):
            return True

        if html.request.get_ascii_input("filled_in") == "filter":
            return True

        return False

    def _page_menu(self, breadcrumb: Breadcrumb, rows: Rows,
                   show_filters: List[Filter]) -> PageMenu:
        if not display_options.enabled(display_options.B):
            return PageMenu()  # No buttons -> no menu

        export_dropdown = [
            PageMenuDropdown(
                name="export",
                title=_("Export"),
                topics=[
                    PageMenuTopic(
                        title=_("Data"),
                        entries=list(self._page_menu_entries_export_data()),
                    ),
                    PageMenuTopic(
                        title=_("Reports"),
                        entries=list(self._page_menu_entries_export_reporting(rows)),
                    ),
                ],
            ),
        ]

        menu = PageMenu(
            dropdowns=self._page_menu_dropdown_commands() +
            self._page_menu_dropdowns_context(rows) + self._page_menu_dropdown_add_to() +
            export_dropdown,
            breadcrumb=breadcrumb,
        )

        self._extend_display_dropdown(menu, show_filters)
        self._extend_help_dropdown(menu)

        return menu

    def _page_menu_dropdown_commands(self) -> List[PageMenuDropdown]:
        if not display_options.enabled(display_options.C):
            return []

        return [
            PageMenuDropdown(
                name="commands",
                title=_("Commands"),
                topics=[
                    PageMenuTopic(
                        title=_("On selected objects"),
                        entries=list(self._page_menu_entries_selected_objects()),
                    ),
                    make_checkbox_selection_topic(is_enabled=self.view.checkboxes_displayed),
                ],
            )
        ]

    def _page_menu_entries_selected_objects(self) -> Iterator[PageMenuEntry]:
        info_name: InfoName = self.view.datasource.infos[0]
        by_group = _get_command_groups(info_name)

        for _group_class, commands in sorted(by_group.items(), key=lambda x: x[0]().sort_index):
            for command in commands:
                yield PageMenuEntry(
                    title=command.title,
                    icon_name=command.icon_name,
                    item=PageMenuPopup(self._render_command_form(info_name, command)),
                    name="command_%s" % command.ident,
                    is_enabled=_should_show_command_form(self.view.datasource),
                    is_show_more=command.is_show_more,
                    is_shortcut=command.is_shortcut,
                    is_suggested=command.is_suggested,
                    css_classes=["command"],
                )

    def _page_menu_dropdowns_context(self, rows: Rows) -> List[PageMenuDropdown]:
        return _get_context_page_menu_dropdowns(self.view, rows, mobile=False)

    def _page_menu_entries_export_data(self) -> Iterator[PageMenuEntry]:
        if not config.user.may("general.csv_export"):
            return

        yield PageMenuEntry(
            title=_("Export CSV"),
            icon_name="download_csv",
            item=make_simple_link(makeuri(global_request, [("output_format", "csv_export")])),
        )

        yield PageMenuEntry(
            title=_("Export JSON"),
            icon_name="download_json",
            item=make_simple_link(makeuri(global_request, [("output_format", "json_export")])),
        )

    def _page_menu_entries_export_reporting(self, rows: Rows) -> Iterator[PageMenuEntry]:
        if not config.reporting_available():
            return

        if not config.user.may("general.instant_reports"):
            return

        yield PageMenuEntry(
            title=_("This view as PDF"),
            icon_name="report",
            item=make_simple_link(makeuri(global_request, [], filename="report_instant.py")),
        )

        # Link related reports
        yield from collect_context_links(self.view, rows, only_types=["reports"])

    def _extend_display_dropdown(self, menu: PageMenu, show_filters: List[Filter]) -> None:
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())

        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("View layout"),
                entries=list(self._page_menu_entries_view_layout()),
            ))

        if display_options.enabled(display_options.D):
            display_dropdown.topics.insert(
                0,
                PageMenuTopic(
                    title=_("Format"),
                    entries=list(self._page_menu_entries_view_format()),
                ))

        if display_options.enabled(display_options.F):
            display_dropdown.topics.insert(
                0,
                PageMenuTopic(
                    title=_("Filter"),
                    entries=list(self._page_menu_entries_filter(show_filters)),
                ))

    def _page_menu_entries_filter(self, show_filters: List[Filter]) -> Iterator[PageMenuEntry]:
        is_filter_set = html.request.var("filled_in") == "filter"

        yield PageMenuEntry(
            title=_("Filter view"),
            icon_name="filters_set" if is_filter_set else "filters",
            item=PageMenuSidePopup(self._render_filter_form(show_filters)),
            name="filters",
            is_shortcut=True,
        )

    def _page_menu_entries_view_format(self) -> Iterator[PageMenuEntry]:
        painter_options = PainterOptions.get_instance()
        yield PageMenuEntry(
            title=_("Modify display options"),
            icon_name="painteroptions",
            item=PageMenuPopup(self._render_painter_options_form()),
            name="display_painter_options",
            is_enabled=painter_options.painter_option_form_enabled(),
        )

    def _page_menu_entries_view_layout(self) -> Iterator[PageMenuEntry]:
        checkboxes_toggleable = self.view.layout.can_display_checkboxes and not self.view.checkboxes_enforced
        yield PageMenuEntry(
            title=_("Hide checkboxes") if self.view.checkboxes_displayed else _("Show checkboxes"),
            icon_name="checkbox",
            item=make_simple_link(
                makeuri(
                    global_request,
                    [("show_checkboxes", "0" if self.view.checkboxes_displayed else "1")],
                )),
            is_shortcut=True,
            is_suggested=True,
            is_enabled=checkboxes_toggleable,
        )

        if display_options.enabled(display_options.E) and config.user.may("general.edit_views"):
            url_vars: HTTPVariables = [
                ("back", html.request.requested_url),
                ("load_name", self.view.name),
            ]

            if self.view.spec["owner"] != config.user.id:
                url_vars.append(("load_user", self.view.spec["owner"]))

            url = makeuri_contextless(global_request, url_vars, filename="edit_view.py")

            yield PageMenuEntry(
                title=_("Customize view"),
                icon_name="edit",
                item=make_simple_link(url),
            )

    def _page_menu_dropdown_add_to(self) -> List[PageMenuDropdown]:
        return visuals.page_menu_dropdown_add_to_visual(add_type="view", name=self.view.name)

    def _render_filter_form(self, show_filters: List[Filter]) -> str:
        if not display_options.enabled(display_options.F) or not show_filters:
            return ""

        with html.plugged():
            show_filter_form(self.view, show_filters)
            return html.drain()

    def _render_painter_options_form(self) -> str:
        with html.plugged():
            painter_options = PainterOptions.get_instance()
            painter_options.show_form(self.view)
            return html.drain()

    def _render_command_form(self, info_name: InfoName, command: Command) -> str:
        with html.plugged():
            if not _should_show_command_form(self.view.datasource):
                return ""

            # TODO: Make unique form names (object IDs), investigate whether or not something
            # depends on the form name "actions"
            html.begin_form("actions")
            # TODO: Are these variables still needed
            html.hidden_field("_do_actions", "yes")
            html.hidden_field("actions", "yes")

            command.render(info_name)

            html.hidden_fields()
            html.end_form()

            return html.drain()

    def _extend_help_dropdown(self, menu: PageMenu) -> None:
        # TODO
        #menu.add_manual_reference(title=_("Host administration"), article_name="wato_hosts")
        #menu.add_youtube_reference(title=_("Episode 3: Monitoring Windows"),
        #                           youtube_id="iz8S9TGGklQ")
        pass


# Load all view plugins
def load_plugins(force):
    global loaded_with_language

    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        clear_alarm_sound_states()
        return

    utils.load_web_plugins("views", globals())
    utils.load_web_plugins('icons', globals())
    utils.load_web_plugins("perfometer", globals())
    clear_alarm_sound_states()

    transform_old_dict_based_icons()

    # TODO: Kept for compatibility with pre 1.6 plugins. Plugins will not be used anymore, but an error
    # will be displayed.
    if multisite_painter_options:
        raise MKGeneralException("Found legacy painter option plugins: %s. You will either have to "
                                 "remove or migrate them." %
                                 ", ".join(multisite_painter_options.keys()))
    if multisite_layouts:
        raise MKGeneralException("Found legacy layout plugins: %s. You will either have to "
                                 "remove or migrate them." % ", ".join(multisite_layouts.keys()))
    if multisite_datasources:
        raise MKGeneralException("Found legacy data source plugins: %s. You will either have to "
                                 "remove or migrate them." %
                                 ", ".join(multisite_datasources.keys()))

    # TODO: Kept for compatibility with pre 1.6 plugins
    for cmd_spec in multisite_commands:
        register_legacy_command(cmd_spec)

    cmk.gui.plugins.views.inventory.declare_inventory_columns()

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_painters.items():
        register_painter(ident, spec)

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_sorters.items():
        register_sorter(ident, spec)

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()

    visuals.declare_visual_permissions('views', _("views"))

    # Declare permissions for builtin views
    for name, view_spec in multisite_builtin_views.items():
        declare_permission("view.%s" % name, format_view_title(name, view_spec),
                           "%s - %s" % (name, _u(view_spec["description"])),
                           config.builtin_role_ids)

    # Make sure that custom views also have permissions
    config.declare_dynamic_permissions(lambda: visuals.declare_custom_permissions('views'))


# Transform pre 1.6 icon plugins. Deprecate this one day.
def transform_old_dict_based_icons():
    for icon_id, icon in multisite_icons_and_actions.items():
        icon_class = type(
            "LegacyIcon%s" % icon_id.title(), (Icon,), {
                "_ident": icon_id,
                "_icon_spec": icon,
                "ident": classmethod(lambda cls: cls._ident),
                "sort_index": lambda self: self._icon_spec.get("sort_index", 30),
                "toplevel": lambda self: self._icon_spec.get("toplevel", False),
                "render": lambda self, *args: self._icon_spec["paint"](*args),
                "columns": lambda self: self._icon_spec.get("columns", []),
                "host_columns": lambda self: self._icon_spec.get("host_columns", []),
                "service_columns": lambda self: self._icon_spec.get("service_columns", []),
            })

        icon_and_action_registry.register(icon_class)


def _register_tag_plugins():
    if getattr(_register_tag_plugins, "_config_hash", None) == _calc_config_hash():
        return  # No re-register needed :-)
    _register_host_tag_painters()
    _register_host_tag_sorters()
    setattr(_register_tag_plugins, "_config_hash", _calc_config_hash())


def _calc_config_hash() -> int:
    return hash(repr(config.tags.get_dict_format()))


config.register_post_config_load_hook(_register_tag_plugins)


def _register_host_tag_painters():
    # first remove all old painters to reflect delted painters during runtime
    for key in list(painter_registry.keys()):
        if key.startswith('host_tag_'):
            painter_registry.unregister(key)

    for tag_group in config.tags.tag_groups:
        if tag_group.topic:
            long_title = tag_group.topic + ' / ' + tag_group.title
        else:
            long_title = tag_group.title

        ident = "host_tag_" + tag_group.id
        spec = {
            "title": _("Host tag:") + ' ' + long_title,
            "short": tag_group.title,
            "columns": ["host_tags"],
        }
        cls = type(
            "HostTagPainter%s" % str(tag_group.id).title(),
            (Painter,),
            {
                "_ident": ident,
                "_spec": spec,
                "_tag_group_id": tag_group.id,
                "ident": property(lambda self: self._ident),
                "title": lambda self, cell: self._spec["title"],
                "short_title": lambda self, cell: self._spec["short"],
                "columns": property(lambda self: self._spec["columns"]),
                "render": lambda self, row, cell: _paint_host_tag(row, self._tag_group_id),
                # Use title of the tag value for grouping, not the complete
                # dictionary of custom variables!
                "group_by": lambda self, row: _paint_host_tag(row, self._tag_group_id)[1],
            })
        painter_registry.register(cls)


def _paint_host_tag(row, tgid):
    return "", _get_tag_group_value(row, "host", tgid)


def _register_host_tag_sorters():
    for tag_group in config.tags.tag_groups:
        register_sorter(
            "host_tag_" + str(tag_group.id), {
                "_tag_group_id": tag_group.id,
                "title": _("Host tag:") + ' ' + tag_group.title,
                "columns": ["host_tags"],
                "cmp": lambda self, r1, r2: _cmp_host_tag(r1, r2, self._spec["_tag_group_id"]),
            })


def _cmp_host_tag(r1, r2, tgid):
    host_tag_1 = _get_tag_group_value(r1, "host", tgid)
    host_tag_2 = _get_tag_group_value(r2, "host", tgid)
    return (host_tag_1 > host_tag_2) - (host_tag_1 < host_tag_2)


def _get_tag_group_value(row, what, tag_group_id):
    tag_id = get_tag_groups(row, "host").get(tag_group_id)

    tag_group = config.tags.get_tag_group(tag_group_id)
    if tag_group:
        label = dict(tag_group.get_tag_choices()).get(tag_id, _("N/A"))
    else:
        label = tag_id

    return label or _("N/A")


#.
#   .--Table of views------------------------------------------------------.
#   |   _____     _     _               __         _                       |
#   |  |_   _|_ _| |__ | | ___    ___  / _| __   _(_) _____      _____     |
#   |    | |/ _` | '_ \| |/ _ \  / _ \| |_  \ \ / / |/ _ \ \ /\ / / __|    |
#   |    | | (_| | |_) | |  __/ | (_) |  _|  \ V /| |  __/\ V  V /\__ \    |
#   |    |_|\__,_|_.__/|_|\___|  \___/|_|     \_/ |_|\___| \_/\_/ |___/    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Show list of all views with buttons for editing                      |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("edit_views")
def page_edit_views():
    cols = [(_('Datasource'), lambda v: data_source_registry[v["datasource"]]().title)]
    visuals.page_list('views', _("Edit Views"), get_all_views(), cols)


#.
#   .--Create View---------------------------------------------------------.
#   |        ____                _        __     ___                       |
#   |       / ___|_ __ ___  __ _| |_ ___  \ \   / (_) _____      __        |
#   |      | |   | '__/ _ \/ _` | __/ _ \  \ \ / /| |/ _ \ \ /\ / /        |
#   |      | |___| | |  __/ (_| | ||  __/   \ V / | |  __/\ V  V /         |
#   |       \____|_|  \___|\__,_|\__\___|    \_/  |_|\___| \_/\_/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Select the view type of the new view                                 |
#   '----------------------------------------------------------------------'

# First step: Select the data source


def DatasourceSelection() -> DropdownChoice:
    """Create datasource selection valuespec, also for other modules"""
    return DropdownChoice(
        title=_('Datasource'),
        help=_('The datasources define which type of objects should be displayed with this view.'),
        choices=data_source_registry.data_source_choices(),
        default_value='services',
    )


@cmk.gui.pages.register("create_view")
def page_create_view():
    show_create_view_dialog()


def show_create_view_dialog(next_url=None):
    vs_ds = DatasourceSelection()

    ds = 'services'  # Default selection

    title = _('Create view')
    breadcrumb = visuals.visual_page_breadcrumb("views", title, "create")
    html.header(
        title, breadcrumb,
        make_simple_form_page_menu(breadcrumb,
                                   form_name="create_view",
                                   button_name="save",
                                   save_title=_("Continue")))

    if html.request.var('save') and html.check_transaction():
        try:
            ds = vs_ds.from_html_vars('ds')
            vs_ds.validate_value(ds, 'ds')

            if not next_url:
                next_url = makeuri(
                    global_request,
                    [('datasource', ds)],
                    filename="create_view_infos.py",
                )
            else:
                next_url = next_url + '&datasource=%s' % ds
            raise HTTPRedirect(next_url)
        except MKUserError as e:
            html.div(str(e), class_=["error"])
            html.add_user_error(e.varname, e)

    html.begin_form('create_view')
    html.hidden_field('mode', 'create')

    forms.header(_('Select Datasource'))
    forms.section(vs_ds.title())
    vs_ds.render_input('ds', ds)
    html.help(vs_ds.help())
    forms.end()

    html.hidden_fields()
    html.end_form()
    html.footer()


@cmk.gui.pages.register("create_view_infos")
def page_create_view_infos():
    ds_class, ds_name = html.get_item_input("datasource", data_source_registry)
    visuals.page_create_visual('views',
                               ds_class().infos,
                               next_url='edit_view.py?mode=create&datasource=%s&single_infos=%%s' %
                               ds_name)


#.
#   .--Edit View-----------------------------------------------------------.
#   |             _____    _ _ _    __     ___                             |
#   |            | ____|__| (_) |_  \ \   / (_) _____      __              |
#   |            |  _| / _` | | __|  \ \ / /| |/ _ \ \ /\ / /              |
#   |            | |__| (_| | | |_    \ V / | |  __/\ V  V /               |
#   |            |_____\__,_|_|\__|    \_/  |_|\___| \_/\_/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("edit_view")
def page_edit_view():
    visuals.page_edit_visual(
        'views',
        get_all_views(),
        custom_field_handler=render_view_config,
        load_handler=transform_view_to_valuespec_value,
        create_handler=create_view_from_valuespec,
        info_handler=get_view_infos,
    )


def view_choices(only_with_hidden=False):
    choices = [("", "")]
    for name, view in get_permitted_views().items():
        if not only_with_hidden or view['single_infos']:
            title = format_view_title(name, view)
            choices.append(("%s" % name, title))
    return choices


def format_view_title(name, view):
    title_parts = []

    if view.get('mobile', False):
        title_parts.append(_('Mobile'))

    # Don't use the data source title because it does not really look good here
    datasource = data_source_registry[view["datasource"]]()
    infos = datasource.infos
    if "event" in infos:
        title_parts.append(_("Event Console"))
    elif view["datasource"].startswith("inv"):
        title_parts.append(_("HW/SW inventory"))
    elif "aggr" in infos:
        title_parts.append(_("BI"))
    elif "log" in infos:
        title_parts.append(_("Log"))
    elif "service" in infos:
        title_parts.append(_("Services"))
    elif "host" in infos:
        title_parts.append(_("Hosts"))
    elif "hostgroup" in infos:
        title_parts.append(_("Hostgroups"))
    elif "servicegroup" in infos:
        title_parts.append(_("Servicegroups"))

    title_parts.append("%s (%s)" % (_u(view["title"]), name))

    return " - ".join(title_parts)


def view_editor_options():
    return [
        ('mobile', _('Show this view in the Mobile GUI')),
        ('mustsearch', _('Show data only on search')),
        ('force_checkboxes', _('Always show the checkboxes')),
        ('user_sortable', _('Make view sortable by user')),
        ('play_sounds', _('Play alarm sounds')),
    ]


def view_editor_general_properties(ds_name):
    return Dictionary(
        title=_('View Properties'),
        render='form',
        optional_keys=False,
        elements=[
            ('datasource',
             FixedValue(
                 ds_name,
                 title=_('Datasource'),
                 totext=data_source_registry[ds_name]().title,
                 help=_('The datasource of a view cannot be changed.'),
             )),
            ('options',
             ListChoice(
                 title=_('Options'),
                 choices=view_editor_options(),
                 default_value=['user_sortable'],
             )),
            ('browser_reload',
             Integer(
                 title=_('Automatic page reload'),
                 unit=_('seconds'),
                 minvalue=0,
                 help=_('Set to \"0\" to disable the automatic reload.'),
             )),
            ('layout',
             DropdownChoice(
                 title=_('Basic Layout'),
                 choices=layout_registry.get_choices(),
                 default_value='table',
                 sorted=True,
             )),
            ('num_columns',
             Integer(
                 title=_('Number of Columns'),
                 default_value=1,
                 minvalue=1,
                 maxvalue=50,
             )),
            ('column_headers',
             DropdownChoice(
                 title=_('Column Headers'),
                 choices=[
                     ("off", _("off")),
                     ("pergroup", _("once per group")),
                     ("repeat", _("repeat every 20'th row")),
                 ],
                 default_value='pergroup',
             )),
        ],
    )


def view_editor_column_spec(ident, title, ds_name):

    allow_empty = True
    empty_text = None
    if ident == 'columns':
        allow_empty = False
        empty_text = _("Please add at least one column to your view.")

    def column_elements(_painters, painter_type):
        empty_choices: List[DropdownChoiceEntry] = [(None, "")]
        elements = [
            CascadingDropdown(title=_('Column'),
                              choices=painter_choices_with_params(_painters),
                              no_preselect=True,
                              render_sub_vs_page_name="ajax_cascading_render_painer_parameters",
                              render_sub_vs_request_vars={
                                  "ds_name": ds_name,
                                  "painter_type": painter_type,
                              }),
            DropdownChoice(
                title=_('Link'),
                choices=view_choices,
                sorted=True,
            ),
            DropdownChoice(
                title=_('Tooltip'),
                choices=empty_choices + painter_choices(_painters),
            )
        ]
        if painter_type == 'join_painter':
            elements.extend([
                TextUnicode(
                    title=_('of Service'),
                    allow_empty=False,
                ),
                TextUnicode(title=_('Title'))
            ])
        else:
            elements.extend([FixedValue(None, totext=""), FixedValue(None, totext="")])
        # UX/GUI Better ordering of fields and reason for transform
        elements.insert(1, elements.pop(3))
        return elements

    painters = painters_of_datasource(ds_name)
    vs_column: ValueSpec = Tuple(title=_('Column'), elements=column_elements(painters, 'painter'))

    join_painters = join_painters_of_datasource(ds_name)
    if ident == 'columns' and join_painters:
        vs_column = Alternative(
            elements=[
                vs_column,
                Tuple(
                    title=_('Joined column'),
                    help=_("A joined column can display information about specific services for "
                           "host objects in a view showing host objects. You need to specify the "
                           "service description of the service you like to show the data for."),
                    elements=column_elements(join_painters, "join_painter"),
                ),
            ],
            match=lambda x: 1 * (x is not None and x[1] is not None),
        )

    vs_column = Transform(
        vs_column,
        back=lambda value: (value[0], value[2], value[3], value[1], value[4]),
        forth=lambda value: (value[0], value[3], value[1], value[2], value[4])
        if value is not None else None,
    )
    return (ident,
            Dictionary(
                title=title,
                render='form',
                optional_keys=False,
                elements=[
                    (ident,
                     ListOf(
                         vs_column,
                         title=title,
                         add_label=_('Add column'),
                         allow_empty=allow_empty,
                         empty_text=empty_text,
                     )),
                ],
            ))


def view_editor_sorter_specs(view):
    def _sorter_choices(view):
        ds_name = view['datasource']

        for name, p in sorters_of_datasource(ds_name).items():
            yield name, get_sorter_title_for_choices(p)

        for painter_spec in view.get('painters', []):
            if isinstance(painter_spec[0], tuple) and painter_spec[0][0] in [
                    "svc_metrics_hist", "svc_metrics_forecast"
            ]:
                hist_sort = sorters_of_datasource(ds_name).get(painter_spec[0][0])
                uuid = painter_spec[0][1].get('uuid', "")
                if hist_sort and uuid:
                    title = "History" if "hist" in painter_spec[0][0] else "Forecast"
                    yield ('%s:%s' % (painter_spec[0][0], uuid),
                           "Services: Metric %s - Column: %s" %
                           (title, painter_spec[0][1]['column_title']))

    return ('sorting',
            Dictionary(
                title=_('Sorting'),
                render='form',
                optional_keys=False,
                elements=[
                    ('sorters',
                     ListOf(
                         Tuple(
                             elements=[
                                 DropdownChoice(
                                     title=_('Column'),
                                     choices=list(_sorter_choices(view)),
                                     sorted=True,
                                     no_preselect=True,
                                 ),
                                 DropdownChoice(
                                     title=_('Order'),
                                     choices=[(False, _("Ascending")), (True, _("Descending"))],
                                 ),
                             ],
                             orientation='horizontal',
                         ),
                         title=_('Sorting'),
                         add_label=_('Add sorter'),
                     )),
                ],
            ))


@page_registry.register_page("ajax_cascading_render_painer_parameters")
class PageAjaxCascadingRenderPainterParameters(AjaxPage):
    def page(self):
        request = html.get_request()

        if request["painter_type"] == "painter":
            painters = painters_of_datasource(request["ds_name"])
        elif request["painter_type"] == "join_painter":
            painters = join_painters_of_datasource(request["ds_name"])
        else:
            raise NotImplementedError()

        vs = CascadingDropdown(choices=painter_choices_with_params(painters))
        sub_vs = self._get_sub_vs(vs, ast.literal_eval(request["choice_id"]))
        value = ast.literal_eval(request["encoded_value"])

        with html.plugged():
            vs.show_sub_valuespec(request["varprefix"], sub_vs, value)
            return {"html_code": html.drain()}

    def _get_sub_vs(self, vs, choice_id):
        for val, _title, sub_vs in vs.choices():
            if val == choice_id:
                return sub_vs
        raise MKGeneralException("Invaild choice")


def render_view_config(view, general_properties=True):
    ds_name = view.get("datasource", html.request.var("datasource"))
    if not ds_name:
        raise MKInternalError(_("No datasource defined."))
    if ds_name not in data_source_registry:
        raise MKInternalError(_('The given datasource is not supported.'))

    view['datasource'] = ds_name

    if general_properties:
        view_editor_general_properties(ds_name).render_input('view', view.get('view'))

    for ident, vs in [
            view_editor_column_spec('columns', _('Columns'), ds_name),
            view_editor_sorter_specs(view),
            view_editor_column_spec('grouping', _('Grouping'), ds_name),
    ]:
        vs.render_input(ident, view.get(ident))


# Is used to change the view structure to be compatible to
# the valuespec This needs to perform the inverted steps of the
# transform_valuespec_value_to_view() function. FIXME: One day we should
# rewrite this to make no transform needed anymore
def transform_view_to_valuespec_value(view):
    view["view"] = {}  # Several global variables are put into a sub-dict
    # Only copy our known keys. Reporting element, etc. might have their own keys as well
    for key in ["datasource", "browser_reload", "layout", "num_columns", "column_headers"]:
        if key in view:
            view["view"][key] = view[key]

    view["view"]['options'] = []
    for key, _title in view_editor_options():
        if view.get(key):
            view['view']['options'].append(key)

    view['visibility'] = {}
    for key in ['hidden', 'hidebutton', 'public']:
        if view.get(key):
            view['visibility'][key] = view[key]

    view['grouping'] = {"grouping": view.get('group_painters', [])}
    view['sorting'] = {"sorters": view.get('sorters', {})}
    view['columns'] = {"columns": view.get('painters', [])}


def transform_valuespec_value_to_view(ident, attrs):
    # Transform some valuespec specific options to legacy view format.
    # We do not want to change the view data structure at the moment.

    if ident == 'view':
        options = attrs.pop("options", [])
        if options:
            for option, _title in view_editor_options():
                attrs[option] = option in options

        return attrs

    if ident == 'sorting':
        return attrs

    if ident == 'grouping':
        return {'group_painters': attrs['grouping']}

    if ident == 'columns':
        return {'painters': [PainterSpec(*v) for v in attrs['columns']]}

    return {ident: attrs}


# Extract properties of view from HTML variables and construct
# view object, to be used for saving or displaying
#
# old_view is the old view dict which might be loaded from storage.
# view is the new dict object to be updated.
def create_view_from_valuespec(old_view, view):
    ds_name = old_view.get('datasource', html.request.var('datasource'))
    view['datasource'] = ds_name

    def update_view(ident, vs):
        attrs = vs.from_html_vars(ident)
        vs.validate_value(attrs, ident)
        view.update(transform_valuespec_value_to_view(ident, attrs))

    for ident, vs in [('view', view_editor_general_properties(ds_name)),
                      view_editor_column_spec('columns', _('Columns'), ds_name),
                      view_editor_column_spec('grouping', _('Grouping'), ds_name)]:
        update_view(ident, vs)

    update_view(*view_editor_sorter_specs(view))
    return view


#.
#   .--Display View--------------------------------------------------------.
#   |      ____  _           _              __     ___                     |
#   |     |  _ \(_)___ _ __ | | __ _ _   _  \ \   / (_) _____      __      |
#   |     | | | | / __| '_ \| |/ _` | | | |  \ \ / /| |/ _ \ \ /\ / /      |
#   |     | |_| | \__ \ |_) | | (_| | |_| |   \ V / | |  __/\ V  V /       |
#   |     |____/|_|___/ .__/|_|\__,_|\__, |    \_/  |_|\___| \_/\_/        |
#   |                 |_|            |___/                                 |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def show_filter_form(view: View, show_filters: List[Filter]) -> None:
    visuals.show_filter_form(info_list=view.datasource.infos,
                             mandatory_filters=[],
                             context={f.ident: {} for f in show_filters if f.available()},
                             page_name=view.name,
                             reset_ajax_page="ajax_initial_view_filters")


class ABCAjaxInitialFilters(AjaxPage):
    @abc.abstractmethod
    def _get_context(self, page_name: str) -> Dict:
        raise NotImplementedError()

    def page(self) -> Dict[str, str]:
        request = self.webapi_request()
        varprefix = request.get("varprefix", "")
        page_name = request.get("page_name", "")
        context = self._get_context(page_name)
        page_request_vars = request.get("page_request_vars")
        assert isinstance(page_request_vars, dict)
        vs_filters = visuals.VisualFilterListWithAddPopup(info_list=page_request_vars["infos"],
                                                          ignore=page_request_vars["ignore"])
        with html.plugged():
            vs_filters.render_input(varprefix, context)
            return {"filters_html": html.drain()}


@page_registry.register_page("ajax_initial_view_filters")
class AjaxInitialViewFilters(ABCAjaxInitialFilters):
    def _get_context(self, page_name: str) -> Dict:
        # Obtain the visual filters and the view context
        view_name = page_name
        try:
            view_spec = get_permitted_views()[view_name]
        except KeyError:
            raise MKUserError("view_name", _("The requested item %s does not exist") % view_name)

        datasource = data_source_registry[view_spec["datasource"]]()
        show_filters = visuals.filters_of_visual(view_spec,
                                                 datasource.infos,
                                                 link_filters=datasource.link_filters)
        show_filters = visuals.visible_filters_of_visual(view_spec, show_filters)
        view_context = view_spec.get("context", {})

        # Return a visual filters dict filled with the view context values
        return {
            f.ident: view_context[f.ident] if f.ident in view_context else {}
            for f in show_filters
            if f.available()
        }


@cmk.gui.pages.register("view")
def page_view():
    """Central entry point for the initial HTML page rendering of a view"""
    view_spec, view_name = html.get_item_input("view_name", get_permitted_views())

    _patch_view_context(view_spec)

    datasource = data_source_registry[view_spec["datasource"]]()
    context = visuals.get_merged_context(
        visuals.get_context_from_uri_vars(datasource.infos, single_infos=view_spec["single_infos"]),
        view_spec["context"],
    )

    view = View(view_name, view_spec, context)
    view.row_limit = get_limit()
    view.only_sites = visuals.get_only_sites_from_context(context)

    view.user_sorters = get_user_sorters()
    view.want_checkboxes = get_want_checkboxes()

    # Gather the page context which is needed for the "add to visual" popup menu
    # to add e.g. views to dashboards or reports
    html.set_page_context(context)

    painter_options = PainterOptions.get_instance()
    painter_options.load(view.name)
    painter_options.update_from_url(view)
    view_renderer = GUIViewRenderer(view, show_buttons=True)
    process_view(view, view_renderer)


def _patch_view_context(view_spec: ViewSpec) -> None:
    """Apply some hacks that are needed because for some edge cases in the view / visuals / context
    imlementation"""
    # FIXME TODO HACK to make grouping single contextes possible on host/service infos
    # Is hopefully cleaned up soon.
    # This is also somehow connected to the datasource.link_filters hack hat has been created for
    # linking hosts / services with groups
    if view_spec["datasource"] in ['hosts', 'services']:
        if html.request.has_var('hostgroup') and not html.request.has_var("opthost_group"):
            html.request.set_var("opthost_group", html.request.get_str_input_mandatory("hostgroup"))
        if html.request.has_var('servicegroup') and not html.request.has_var("optservice_group"):
            html.request.set_var("optservice_group",
                                 html.request.get_str_input_mandatory("servicegroup"))

    # TODO: Another hack :( Just like the above one: When opening the view "ec_events_of_host",
    # which is of single context "host" using a host name of a unrelated event, the list of
    # events is always empty since the single context filter "host" is sending a "host_name = ..."
    # filter to livestatus which is not matching a "unrelated event". Instead the filter event_host
    # needs to be used.
    # But this may only be done for the unrelated events view. The "ec_events_of_monhost" view still
    # needs the filter. :-/
    # Another idea: We could change these views to non single context views, but then we would not
    # be able to show the buttons to other host related views, which is also bad. So better stick
    # with the current mode.
    if _is_ec_unrelated_host_view(view_spec):
        # Set the value for the event host filter
        if not html.request.has_var("event_host") and html.request.has_var("host"):
            html.request.set_var("event_host", html.request.get_str_input_mandatory("host"))


def process_view(view: View, view_renderer: ABCViewRenderer) -> None:
    """Rendering all kind of views"""
    if html.request.var("mode") == "availability":
        _process_availability_view(view)
    else:
        _process_regular_view(view, view_renderer)


def _process_regular_view(view: View, view_renderer: ABCViewRenderer) -> None:
    all_active_filters = _get_view_filters(view)
    unfiltered_amount_of_rows, rows = _get_view_rows(view, all_active_filters, only_count=False)

    if html.output_format != "html":
        _export_view(view, rows)
    else:
        _show_view(view, view_renderer, unfiltered_amount_of_rows, rows)


def _process_availability_view(view: View) -> None:
    all_active_filters = _get_view_filters(view)
    filterheaders = get_livestatus_filter_headers(view, all_active_filters)

    display_options.load_from_html()

    # Fork to availability view. We just need the filter headers, since we do not query the normal
    # hosts and service table, but "statehist". This is *not* true for BI availability, though (see
    # later)
    if "aggr" not in view.datasource.infos or html.request.var("timeline_aggr"):
        cmk.gui.plugins.views.availability.show_availability_page(view, filterheaders)
        return

    _unfiltered_amount_of_rows, rows = _get_view_rows(view, all_active_filters, only_count=False)
    cmk.gui.plugins.views.availability.show_bi_availability(view, rows)


# TODO: Use livestatus Stats: instead of fetching rows?
def get_row_count(view: View) -> int:
    """Returns the number of rows shown by a view"""
    all_active_filters = _get_view_filters(view)
    # This must not modify the request variables of the view currently being processed. It would be
    # ideal to not deal with the global request variables data structure at all, but that would
    # first need a rewrite of the visual filter processing.
    with html.stashed_vars():
        _unfiltered_amount_of_rows, rows = _get_view_rows(view, all_active_filters, only_count=True)
    return len(rows)


# TODO: Move to View
# TODO: Investigate and cleanup the side effect of setting the HTTP request variables.
def _get_view_filters(view: View) -> List[Filter]:
    # Now populate the HTML vars with context vars from the view definition. Hard
    # coded default values are treated differently:
    #
    # a) single context vars of the view are enforced
    # b) multi context vars can be overwritten by existing HTML vars
    visuals.add_context_to_uri_vars(view.spec["context"], view.spec["single_infos"])

    # Check that all needed information for configured single contexts are available
    visuals.verify_single_infos(view.spec, view.context)

    return _get_all_active_filters(view)


def _get_view_rows(view: View,
                   all_active_filters: List[Filter],
                   only_count: bool = False) -> _Tuple[int, Rows]:
    rows = _fetch_view_rows(view, all_active_filters, only_count)

    # Sorting - use view sorters and URL supplied sorters
    _sort_data(view, rows, view.sorters)

    unfiltered_amount_of_rows = len(rows)

    # Apply non-Livestatus filters
    for filter_ in all_active_filters:
        rows = filter_.filter_table(rows)

    return unfiltered_amount_of_rows, rows


def _fetch_view_rows(view: View, all_active_filters: List[Filter], only_count: bool) -> Rows:
    """Fetches the view rows from livestatus

    Besides gathering the information from livestatus it also joins the rows with other information.
    For the moment this is:

    - Livestatus table joining (e.g. Adding service row info to host rows (For join painters))
    - Add HW/SW inventory data when needed
    - Add SLA data when needed
    """
    filterheaders = get_livestatus_filter_headers(view, all_active_filters)
    headers = filterheaders + view.spec.get("add_headers", "")

    # Fetch data. Some views show data only after pressing [Search]
    if (only_count or (not view.spec.get("mustsearch")) or
            html.request.var("filled_in") in ["filter", 'actions', 'confirm', 'painteroptions']):
        columns = _get_needed_regular_columns(view.group_cells + view.row_cells, view.sorters,
                                              view.datasource)

        rows: Rows = view.datasource.table.query(view, columns, headers, view.only_sites,
                                                 view.row_limit, all_active_filters)

        # Now add join information, if there are join columns
        if view.join_cells:
            _do_table_join(view, rows, filterheaders, view.sorters)

        # If any painter, sorter or filter needs the information about the host's
        # inventory, then we load it and attach it as column "host_inventory"
        if _is_inventory_data_needed(view.group_cells, view.row_cells, view.sorters,
                                     all_active_filters):
            _add_inventory_data(rows)

        if not cmk_version.is_raw_edition():
            _add_sla_data(view, rows)

        return rows
    return []


def _show_view(view: View, view_renderer: ABCViewRenderer, unfiltered_amount_of_rows: int,
               rows: Rows) -> None:
    display_options.load_from_html()

    # Load from hard painter options > view > hard coded default
    painter_options = PainterOptions.get_instance()
    num_columns = painter_options.get("num_columns", view.spec.get("num_columns", 1))
    browser_reload = painter_options.get("refresh", view.spec.get("browser_reload", None))

    force_checkboxes = view.spec.get("force_checkboxes", False)
    show_checkboxes = force_checkboxes or html.request.var('show_checkboxes', '0') == '1'

    # Not all filters are really shown later in show_filter_form(), because filters which
    # have a hardcoded value are not changeable by the user
    show_filters = visuals.filters_of_visual(view.spec,
                                             view.datasource.infos,
                                             link_filters=view.datasource.link_filters)
    show_filters = visuals.visible_filters_of_visual(view.spec, show_filters)

    # Set browser reload
    if browser_reload and display_options.enabled(display_options.R):
        html.set_browser_reload(browser_reload)

    if config.enable_sounds and config.sounds:
        for row in rows:
            save_state_for_playing_alarm_sounds(row)

    # Until now no single byte of HTML code has been output.
    # Now let's render the view
    view_renderer.render(rows, view.group_cells, view.row_cells, show_checkboxes, num_columns,
                         show_filters, unfiltered_amount_of_rows)


def _get_all_active_filters(view: View) -> 'List[Filter]':
    # Always allow the users to specify all allowed filters using the URL
    use_filters = list(visuals.filters_allowed_for_infos(view.datasource.infos).values())

    # See process_view() for more information about this hack
    if _is_ec_unrelated_host_view(view.spec):
        # Remove the original host name filter
        use_filters = [f for f in use_filters if f.ident != "host"]

    use_filters = [f for f in use_filters if f.available()]

    for filt in use_filters:
        # TODO: Clean this up! E.g. make the Filter class implement a default method
        if hasattr(filt, 'derived_columns'):
            filt.derived_columns(view)  # type: ignore[attr-defined]

    return use_filters


def _export_view(view: View, rows: Rows) -> None:
    """Shows the views data in one of the supported machine readable formats"""
    layout = view.layout
    if html.output_format == "csv" and layout.has_individual_csv_export:
        layout.csv_export(rows, view.spec, view.group_cells, view.row_cells)
        return

    exporter = exporter_registry.get(html.output_format)
    if not exporter:
        raise MKUserError("output_format",
                          _("Output format '%s' not supported") % html.output_format)

    exporter.handler(view, rows)


def _is_ec_unrelated_host_view(view_spec: ViewSpec) -> bool:
    # The "name" is not set in view report elements
    return (view_spec["datasource"] in ["mkeventd_events", "mkeventd_history"] and
            "host" in view_spec["single_infos"] and view_spec.get("name") != "ec_events_of_monhost")


def _get_needed_regular_columns(cells: List[Cell], sorters: List[SorterEntry],
                                datasource: ABCDataSource) -> List[ColumnName]:
    """Compute the list of all columns we need to query via Livestatus

    Those are: (1) columns used by the sorters in use, (2) columns use by column- and group-painters
    in use and - note - (3) columns used to satisfy external references (filters) of views we link
    to. The last bit is the trickiest. Also compute this list of view options use by the painters
    """
    # BI availability needs aggr_tree
    # TODO: wtf? a full reset of the list? Move this far away to a special place!
    if html.request.var("mode") == "availability" and "aggr" in datasource.infos:
        return ["aggr_tree", "aggr_name", "aggr_group"]

    columns = columns_of_cells(cells)

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for entry in sorters:
        columns.update(entry.sorter.columns)

    # Add key columns, needed for executing commands
    columns.update(datasource.keys)

    # Add idkey columns, needed for identifying the row
    columns.update(datasource.id_keys)

    # Remove (implicit) site column
    try:
        columns.remove("site")
    except KeyError:
        pass

    # In the moment the context buttons are shown, the link_from mechanism is used
    # to decide to which other views/dashboards the context buttons should link to.
    # This decision is partially made on attributes of the object currently shown.
    # E.g. on a "single host" page the host labels are needed for the decision.
    # This is currently realized explicitly until we need a more flexible mechanism.
    if display_options.enabled(display_options.B) \
        and "host" in datasource.infos:
        columns.add("host_labels")

    return list(columns)


# TODO: When this is used by the reporting then *all* filters are active.
# That way the inventory data will always be loaded. When we convert this to the
# visuals principle the we need to optimize this.
def get_livestatus_filter_headers(view: View, all_active_filters: 'List[Filter]') -> FilterHeaders:
    """Prepare Filter headers for Livestatus"""
    filterheaders = ""
    for filt in all_active_filters:
        try:
            filt.validate_value(filt.value())
            # TODO: Argument does not seem to be used anywhere. Remove it
            header = filt.filter(view.datasource.ident)
        except MKUserError as e:
            html.add_user_error(e.varname, e)
            continue
        filterheaders += header
    return filterheaders


def _get_needed_join_columns(join_cells: List[JoinCell],
                             sorters: List[SorterEntry]) -> List[ColumnName]:
    join_columns = columns_of_cells(join_cells)

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for entry in sorters:
        join_columns.update(entry.sorter.columns)

    # Remove (implicit) site column
    try:
        join_columns.remove("site")
    except KeyError:
        pass

    return list(join_columns)


def _is_inventory_data_needed(group_cells: List[Cell], cells: List[Cell],
                              sorters: List[SorterEntry],
                              all_active_filters: 'List[Filter]') -> bool:
    for cell in cells:
        if cell.has_tooltip():
            if cell.tooltip_painter_name().startswith("inv_"):
                return True

    for entry in sorters:
        if entry.sorter.load_inv:
            return True

    for cell in group_cells + cells:
        if cell.painter().load_inv:
            return True

    for filt in all_active_filters:
        if filt.need_inventory():
            return True

    return False


def _add_inventory_data(rows: Rows) -> None:
    corrupted_inventory_files = []
    for row in rows:
        if "host_name" not in row:
            continue

        try:
            row["host_inventory"] = inventory.load_filtered_and_merged_tree(row)
        except inventory.LoadStructuredDataError:
            # The inventory row may be joined with other rows (perf-o-meter, ...).
            # Therefore we initialize the corrupt inventory tree with an empty tree
            # in order to display all other rows.
            row["host_inventory"] = StructuredDataTree()
            corrupted_inventory_files.append(
                str(inventory.get_short_inventory_filepath(row["host_name"])))

            if corrupted_inventory_files:
                html.add_user_error(
                    "load_structured_data_tree",
                    _("Cannot load HW/SW inventory trees %s. Please remove the corrupted files.") %
                    ", ".join(sorted(corrupted_inventory_files)))


def _add_sla_data(view: View, rows: Rows) -> None:
    import cmk.gui.cee.sla as sla  # pylint: disable=no-name-in-module,import-outside-toplevel
    sla_params = []
    for cell in view.row_cells:
        if cell.painter_name() in ["sla_specific", "sla_fixed"]:
            sla_params.append(cell.painter_parameters())
    if sla_params:
        sla_configurations_container = sla.SLAConfigurationsContainerFactory.create_from_cells(
            sla_params, rows)
        sla.SLAProcessor(sla_configurations_container).add_sla_data_to_rows(rows)


def columns_of_cells(cells: Sequence[Cell]) -> Set[ColumnName]:
    columns: Set[ColumnName] = set()
    for cell in cells:
        columns.update(cell.needed_columns())
    return columns


JoinMasterKey = _Tuple[SiteId, str]
JoinSlaveKey = str


def _do_table_join(view: View, master_rows: Rows, master_filters: str,
                   sorters: List[SorterEntry]) -> None:
    assert view.datasource.join is not None
    join_table, join_master_column = view.datasource.join
    slave_ds = data_source_registry[join_table]()
    assert slave_ds.join_key is not None
    join_slave_column = slave_ds.join_key
    join_cells = view.join_cells
    join_columns = _get_needed_join_columns(join_cells, sorters)

    # Create additional filters
    join_filters = []
    for cell in join_cells:
        join_filters.append(cell.livestatus_filter(join_slave_column))

    join_filters.append("Or: %d" % len(join_filters))
    headers = "%s%s\n" % (master_filters, "\n".join(join_filters))
    rows = slave_ds.table.query(view,
                                columns=list(
                                    set([join_master_column, join_slave_column] + join_columns)),
                                headers=headers,
                                only_sites=view.only_sites,
                                limit=None,
                                all_active_filters=[])

    per_master_entry: Dict[JoinMasterKey, Dict[JoinSlaveKey, Row]] = {}
    current_key: Optional[JoinMasterKey] = None
    current_entry: Optional[Dict[JoinSlaveKey, Row]] = None
    for row in rows:
        master_key = (row["site"], row[join_master_column])
        if master_key != current_key:
            current_key = master_key
            current_entry = {}
            per_master_entry[current_key] = current_entry
        assert current_entry is not None
        current_entry[row[join_slave_column]] = row

    # Add this information into master table in artificial column "JOIN"
    for row in master_rows:
        key = (row["site"], row[join_master_column])
        joininfo = per_master_entry.get(key, {})
        row["JOIN"] = joininfo


g_alarm_sound_states: Set[str] = set([])


def clear_alarm_sound_states() -> None:
    g_alarm_sound_states.clear()


def save_state_for_playing_alarm_sounds(row: 'Row') -> None:
    if not config.enable_sounds or not config.sounds:
        return

    # TODO: Move this to a generic place. What about -1?
    host_state_map = {0: "up", 1: "down", 2: "unreachable"}
    service_state_map = {0: "up", 1: "warning", 2: "critical", 3: "unknown"}

    for state_map, state in [(host_state_map, row.get("host_hard_state", row.get("host_state"))),
                             (service_state_map,
                              row.get("service_last_hard_state", row.get("service_state")))]:
        if state is None:
            continue

        try:
            state_name = state_map[int(state)]
        except KeyError:
            continue

        g_alarm_sound_states.add(state_name)


def play_alarm_sounds() -> None:
    if not config.enable_sounds or not config.sounds:
        return

    url = config.sound_url
    if not url.endswith("/"):
        url += "/"

    for state_name, wav in config.sounds:
        if not state_name or state_name in g_alarm_sound_states:
            html.play_sound(url + wav)
            break  # only one sound at one time


def get_user_sorters() -> List[SorterSpec]:
    """Returns a list of optionally set sort parameters from HTTP request"""
    return _parse_url_sorters(html.request.var("sort"))


def get_want_checkboxes() -> bool:
    """Whether or not the user requested checkboxes to be shown"""
    return html.request.get_integer_input_mandatory("show_checkboxes", 0) == 1


def get_limit() -> Optional[int]:
    """How many data rows may the user query?"""
    limitvar = html.request.var("limit", "soft")
    if limitvar == "hard" and config.user.may("general.ignore_soft_limit"):
        return config.hard_query_limit
    if limitvar == "none" and config.user.may("general.ignore_hard_limit"):
        return None
    return config.soft_query_limit


def _link_to_folder_by_path(path: str) -> str:
    """Return an URL to a certain WATO folder when we just know its path"""
    return makeuri_contextless(
        global_request,
        [("mode", "folder"), ("folder", path)],
        filename="wato.py",
    )


def _link_to_host_by_name(host_name: str) -> str:
    """Return an URL to the edit-properties of a host when we just know its name"""
    return makeuri_contextless(
        global_request,
        [("mode", "edit_host"), ("host", host_name)],
        filename="wato.py",
    )


def _get_context_page_menu_dropdowns(view: View, rows: Rows,
                                     mobile: bool) -> List[PageMenuDropdown]:
    """For the given visual find other visuals to link to

    Based on the (single_infos and infos of the data source) we have different categories,
    for example a single host view has the following categories:

    - Single host
    - Multiple hosts

    Each of these gets a dedicated dropdown which contain entries to the visuals that
    share this context. The entries are grouped by the topics defined by the visuals.
    """
    dropdowns = []

    pagetypes.PagetypeTopics.load()
    topics = pagetypes.PagetypeTopics.get_permitted_instances()

    # First gather a flat list of all visuals to be linked to
    singlecontext_request_vars = visuals.get_singlecontext_html_vars(view.spec["context"],
                                                                     view.spec["single_infos"])
    linked_visuals = list(_collect_linked_visuals(view, rows, singlecontext_request_vars, mobile))

    # Now get the "info+single object" combinations to show dropdown menus for
    for info_name, is_single_info in _get_relevant_infos(view):
        ident = "%s_%s" % (info_name, "single" if is_single_info else "multiple")
        info = visual_info_registry[info_name]()

        dropdown_visuals = _get_visuals_for_page_menu_dropdown(linked_visuals, info, is_single_info)

        # Special hack for host setup links
        if info_name == "host" and is_single_info:
            host_setup_topic = _page_menu_host_setup_topic(view)
        else:
            host_setup_topic = []

        dropdowns.append(
            PageMenuDropdown(
                name=ident,
                title=info.title if is_single_info else info.title_plural,
                topics=host_setup_topic + list(
                    _get_context_page_menu_topics(
                        view,
                        info,
                        is_single_info,
                        topics,
                        dropdown_visuals,
                        singlecontext_request_vars,
                        mobile,
                    )),
            ))

    return dropdowns


def _get_context_page_menu_topics(view: View, info: VisualInfo, is_single_info: bool,
                                  topics: Dict[str, pagetypes.PagetypeTopics],
                                  dropdown_visuals: Iterator[_Tuple[VisualType, Visual]],
                                  singlecontext_request_vars: Dict[str, str],
                                  mobile: bool) -> Iterator[PageMenuTopic]:
    """Create the page menu topics for the given dropdown from the flat linked visuals list"""
    by_topic: Dict[pagetypes.PagetypeTopics, List[PageMenuEntry]] = {}

    for visual_type, visual in sorted(dropdown_visuals,
                                      key=lambda i: (i[1]["sort_index"], i[1]["title"])):
        try:
            topic = topics[visual["topic"]]
        except KeyError:
            topic = topics["other"]

        entry = _make_page_menu_entry_for_visual(visual_type, visual, singlecontext_request_vars,
                                                 mobile)

        by_topic.setdefault(topic, []).append(entry)

    availability_entry = _get_availability_entry(view, info, is_single_info)
    if availability_entry:
        by_topic.setdefault(topics["history"], []).append(availability_entry)

    combined_graphs_entry = _get_combined_graphs_entry(view, info, is_single_info)
    if combined_graphs_entry:
        by_topic.setdefault(topics["history"], []).append(combined_graphs_entry)

    # Return the sorted topics
    for topic, entries in sorted(by_topic.items(), key=lambda e: (e[0].sort_index(), e[0].title())):
        yield PageMenuTopic(
            title=topic.title(),
            entries=entries,
        )


def _get_visuals_for_page_menu_dropdown(
        linked_visuals: List[_Tuple[VisualType, Visual]], info: VisualInfo,
        is_single_info: bool) -> Iterator[_Tuple[VisualType, Visual]]:
    """Extract the visuals for the given dropdown from the flat linked visuals list"""
    for visual_type, visual in linked_visuals:
        if is_single_info and info.ident in visual["single_infos"]:
            yield visual_type, visual
            continue


def _get_relevant_infos(view: View) -> List[_Tuple[InfoName, bool]]:
    """Gather the infos that are relevant for this view"""
    dropdowns = [(info_name, True) for info_name in view.spec["single_infos"]]
    dropdowns += [(info_name, False) for info_name in view.datasource.infos]
    return dropdowns


def collect_context_links(view: View,
                          rows: Rows,
                          mobile: bool = False,
                          only_types: Optional[List[InfoName]] = None) -> Iterator[PageMenuEntry]:
    """Collect all visuals that share a context with visual. For example
    if a visual has a host context, get all relevant visuals."""
    if only_types is None:
        only_types = []

    # compute collections of set single context related request variables needed for this visual
    singlecontext_request_vars = visuals.get_singlecontext_html_vars(view.spec["context"],
                                                                     view.spec["single_infos"])

    for visual_type, visual in _collect_linked_visuals(view, rows, singlecontext_request_vars,
                                                       mobile):
        if only_types and visual_type.ident not in only_types:
            continue

        yield _make_page_menu_entry_for_visual(visual_type, visual, singlecontext_request_vars,
                                               mobile)


def _collect_linked_visuals(view: View, rows: Rows, singlecontext_request_vars: Dict[str, str],
                            mobile: bool) -> Iterator[_Tuple[VisualType, Visual]]:
    for type_name in visual_type_registry.keys():
        if type_name == "reports":
            continue  # Reports are displayed by separate dropdown (Export > Report)

        yield from _collect_linked_visuals_of_type(type_name, view, rows,
                                                   singlecontext_request_vars, mobile)


def _collect_linked_visuals_of_type(type_name: str, view: View, rows: Rows,
                                    singlecontext_request_vars: Dict[str, str],
                                    mobile: bool) -> Iterator[_Tuple[VisualType, Visual]]:
    visual_type = visual_type_registry[type_name]()
    visual_type.load_handler()
    available_visuals = visual_type.permitted_visuals

    for visual in sorted(available_visuals.values(), key=lambda x: x.get('name') or ""):
        if visual == view.spec:
            continue

        if visual.get("hidebutton", False):
            continue  # this visual does not want a button to be displayed

        if not mobile and visual.get('mobile') or mobile and not visual.get('mobile'):
            continue

        # For dashboards and views we currently only show a link button,
        # if the target dashboard/view shares a single info with the
        # current visual.
        if not visual['single_infos'] and not visual_type.multicontext_links:
            continue  # skip non single visuals for dashboard, views

        # We can show a button only if all single contexts of the
        # target visual are known currently
        has_single_contexts = all(var in singlecontext_request_vars
                                  for var in visuals.get_single_info_keys(visual["single_infos"]))
        if not has_single_contexts:
            continue

        # Optional feature of visuals: Make them dynamically available as links or not.
        # This has been implemented for HW/SW inventory views which are often useless when a host
        # has no such information available. For example the "Oracle Tablespaces" inventory view
        # is useless on hosts that don't host Oracle databases.
        vars_values = _get_linked_visual_request_vars(visual, singlecontext_request_vars)
        if not visual_type.link_from(view, rows, visual, vars_values):
            continue

        yield visual_type, visual


def _get_linked_visual_request_vars(visual: Visual,
                                    singlecontext_request_vars: Dict[str, str]) -> HTTPVariables:
    vars_values: HTTPVariables = []
    for var in visuals.get_single_info_keys(visual["single_infos"]):
        vars_values.append((var, singlecontext_request_vars[var]))

    add_site_hint = visuals.may_add_site_hint(visual["name"],
                                              info_keys=list(visual_info_registry.keys()),
                                              single_info_keys=visual["single_infos"],
                                              filter_names=list(dict(vars_values).keys()))

    if add_site_hint and html.request.var('site'):
        vars_values.append(('site', html.request.get_ascii_input_mandatory('site')))
    return vars_values


def _make_page_menu_entry_for_visual(visual_type: VisualType, visual: Visual,
                                     singlecontext_request_vars: Dict[str, str],
                                     mobile: bool) -> PageMenuEntry:
    name = visual["name"]
    vars_values = _get_linked_visual_request_vars(visual, singlecontext_request_vars)

    filename = visual_type.show_url
    if mobile and visual_type.show_url == 'view.py':
        filename = 'mobile_' + visual_type.show_url

    # add context link to this visual. For reports we put in
    # the *complete* context, even the non-single one.
    if visual_type.multicontext_links:
        uri = makeuri(global_request, [(visual_type.ident_attr, name)], filename=filename)

    else:
        # For views and dashboards currently the current filter settings
        uri = makeuri_contextless(
            global_request,
            vars_values + [(visual_type.ident_attr, name)],
            filename=filename,
        )

    return PageMenuEntry(title=visual["title"],
                         icon_name=visual.get("icon") or "trans",
                         item=make_simple_link(uri),
                         name="cb_" + name)


def _get_availability_entry(view: View, info: VisualInfo,
                            is_single_info: bool) -> Optional[PageMenuEntry]:
    """Detect whether or not to add an availability link to the dropdown currently being rendered

    In which dropdown to expect the "show availability for current view" link?

    host, service -> service
    host, services -> services
    hosts, services -> services
    hosts, service -> services

    host -> host
    hosts -> hosts

    aggr -> aggr
    aggrs -> aggrs
    """
    if not _show_current_view_availability_context_button(view):
        return None

    if not _show_in_current_dropdown(view, info.ident, is_single_info):
        return None

    return PageMenuEntry(
        title=_("Availability"),
        icon_name="availability",
        item=make_simple_link(makeuri(global_request, [("mode", "availability")])),
    )


def _show_current_view_availability_context_button(view: View) -> bool:
    if not config.user.may("general.see_availability"):
        return False

    if "aggr" in view.datasource.infos:
        return True

    return view.datasource.ident in ["hosts", "services"]


def _get_combined_graphs_entry(view: View, info: VisualInfo,
                               is_single_info: bool) -> Optional[PageMenuEntry]:
    """Detect whether or not to add a combined graphs link to the dropdown currently being rendered

    In which dropdown to expect the "All metrics of same type in one graph" link?

    """
    if not _show_combined_graphs_context_button(view):
        return None

    if not _show_in_current_dropdown(view, info.ident, is_single_info):
        return None

    url = makeuri(
        global_request,
        [
            ("single_infos", ",".join(view.spec["single_infos"])),
            ("datasource", view.datasource.ident),
            ("view_title", view_title(view.spec)),
        ],
        filename="combined_graphs.py",
    )
    return PageMenuEntry(
        title=_("All metrics of same type in one graph"),
        icon_name="pnp",
        item=make_simple_link(url),
    )


def _show_combined_graphs_context_button(view: View) -> bool:
    if not config.combined_graphs_available():
        return False

    return view.datasource.ident in ["hosts", "services", "hostsbygroup", "servicesbygroup"]


def _show_in_current_dropdown(view: View, info_name: InfoName, is_single_info: bool) -> bool:
    if info_name == "aggr_group":
        return False  # Not showing for groups

    if info_name == "service" and is_single_info:
        return sorted(view.spec["single_infos"]) == ["host", "service"]

    matches_datasource = _dropdown_matches_datasource(info_name, view.datasource)

    if info_name == "service" and not is_single_info:
        return "service" not in view.spec["single_infos"] and matches_datasource

    if is_single_info:
        return view.spec["single_infos"] == [info_name] and matches_datasource

    return info_name not in view.spec["single_infos"] and matches_datasource


def _dropdown_matches_datasource(info_name: InfoName, datasource: ABCDataSource) -> bool:
    if info_name == "host":
        return datasource.ident == "hosts"
    if info_name == "service":
        return datasource.ident == "services"
    if info_name in ["hostgroup", "servicegroup"]:
        return False
    if info_name == "aggr":
        return "aggr" in datasource.infos

    # This is not generic enough. Generalize once we hit this
    raise ValueError("Can not decide whether or not to show this button: %s, %s" %
                     (info_name, datasource.ident))


def _page_menu_host_setup_topic(view) -> List[PageMenuTopic]:
    if "host" not in view.spec['single_infos']:
        return []

    if not config.wato_enabled:
        return []

    if not config.user.may("wato.use"):
        return []

    if not config.user.may("wato.hosts") and not config.user.may("wato.seeall"):
        return []

    return [PageMenuTopic(
        title=_("Setup"),
        entries=list(_page_menu_entries_host_setup()),
    )]


def _page_menu_entries_host_setup() -> Iterator[PageMenuEntry]:
    host_name = html.request.get_ascii_input_mandatory("host")

    yield PageMenuEntry(
        title=_("Host configuration"),
        icon_name="wato",
        item=make_simple_link(_link_to_host_by_name(host_name)),
    )

    yield PageMenuEntry(
        title=_("Service configuration"),
        icon_name="services",
        item=make_simple_link(
            makeuri_contextless(
                global_request,
                [("mode", "inventory"), ("host", host_name)],
                filename="wato.py",
            )),
    )

    is_cluster = False
    if is_cluster:
        yield PageMenuEntry(
            title=_("Connection tests"),
            icon_name="diagnose",
            item=make_simple_link(
                makeuri_contextless(
                    global_request,
                    [("mode", "diag_host"), ("host", host_name)],
                    filename="wato.py",
                )),
        )

    if config.user.may('wato.rulesets'):
        yield PageMenuEntry(
            title=_("Effective parameters"),
            icon_name="rulesets",
            item=make_simple_link(
                makeuri_contextless(
                    global_request,
                    [("mode", "object_parameters"), ("host", host_name)],
                    filename="wato.py",
                )),
        )


def _sort_data(view: View, data: 'Rows', sorters: List[SorterEntry]) -> None:
    """Sort data according to list of sorters."""
    if not sorters:
        return

    # Handle case where join columns are not present for all rows
    def safe_compare(compfunc: Callable[[Row, Row], int], row1: Row, row2: Row) -> int:
        if row1 is None and row2 is None:
            return 0
        if row1 is None:
            return -1
        if row2 is None:
            return 1
        return compfunc(row1, row2)

    def multisort(e1: Row, e2: Row) -> int:
        for entry in sorters:
            neg = -1 if entry.negate else 1

            if entry.join_key:  # Sorter for join column, use JOIN info
                c = neg * safe_compare(entry.sorter.cmp, e1["JOIN"].get(entry.join_key),
                                       e2["JOIN"].get(entry.join_key))
            else:
                c = neg * entry.sorter.cmp(e1, e2)

            if c != 0:
                return c
        return 0  # equal

    data.sort(key=functools.cmp_to_key(multisort))


def sorters_of_datasource(ds_name):
    return _allowed_for_datasource(sorter_registry, ds_name)


def painters_of_datasource(ds_name: str) -> Dict[str, Painter]:
    return _allowed_for_datasource(painter_registry, ds_name)


def join_painters_of_datasource(ds_name):
    datasource = data_source_registry[ds_name]()
    if datasource.join is None:
        return {}  # no joining with this datasource

    # Get the painters allowed for the join "source" and "target"
    painters = painters_of_datasource(ds_name)
    join_painters_unfiltered = _allowed_for_datasource(painter_registry, datasource.join[0])

    # Filter out painters associated with the "join source" datasource
    join_painters = {}
    for key, val in join_painters_unfiltered.items():
        if key not in painters:
            join_painters[key] = val

    return join_painters


# Filters a list of sorters or painters and decides which of
# those are available for a certain data source
def _allowed_for_datasource(collection, ds_name):
    datasource = data_source_registry[ds_name]()
    infos_available = set(datasource.infos)
    add_columns = datasource.add_columns

    allowed = {}
    for name, plugin_class in collection.items():
        plugin = plugin_class()
        infos_needed = infos_needed_by_painter(plugin, add_columns)
        if len(infos_needed.difference(infos_available)) == 0:
            allowed[name] = plugin
    return allowed


def infos_needed_by_painter(painter, add_columns=None):
    if add_columns is None:
        add_columns = []

    return {c.split("_", 1)[0] for c in painter.columns if c != "site" and c not in add_columns}


def painter_choices(painters: Dict[str, Painter]) -> List[DropdownChoiceEntry]:
    return [(c[0], c[1]) for c in painter_choices_with_params(painters)]


def painter_choices_with_params(painters: Dict[str, Painter]) -> List[CascadingDropdownChoice]:
    return sorted(((name, get_painter_title_for_choices(painter),
                    painter.parameters if painter.parameters else None)
                   for name, painter in painters.items()),
                  key=lambda x: x[1])


def get_sorter_title_for_choices(sorter: Sorter) -> str:
    info_title = "/".join([
        visual_info_registry[info_name]().title_plural
        for info_name in sorted(infos_needed_by_painter(sorter))
    ])

    # TODO: Cleanup the special case for sites. How? Add an info for it?
    if sorter.columns == ["site"]:
        info_title = _("Site")

    return u"%s: %s" % (info_title, sorter.title)


def get_painter_title_for_choices(painter: Painter) -> str:
    info_title = "/".join([
        visual_info_registry[info_name]().title_plural
        for info_name in sorted(infos_needed_by_painter(painter))
    ])

    # TODO: Cleanup the special case for sites. How? Add an info for it?
    if painter.columns == ["site"]:
        info_title = _("Site")

    dummy_cell = Cell(View("", {}, {}), PainterSpec(painter.ident))
    return u"%s: %s" % (info_title, painter.list_title(dummy_cell))


#.
#   .--Commands------------------------------------------------------------.
#   |         ____                                          _              |
#   |        / ___|___  _ __ ___  _ __ ___   __ _ _ __   __| |___          |
#   |       | |   / _ \| '_ ` _ \| '_ ` _ \ / _` | '_ \ / _` / __|         |
#   |       | |__| (_) | | | | | | | | | | | (_| | | | | (_| \__ \         |
#   |        \____\___/|_| |_| |_|_| |_| |_|\__,_|_| |_|\__,_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Functions dealing with external commands send to the monitoring      |
#   | core. The commands themselves are defined as a plugin. Shipped       |
#   | command definitions are in plugins/views/commands.py.                |
#   | We apologize for the fact that we one time speak of "commands" and   |
#   | the other time of "action". Both is the same here...                 |
#   '----------------------------------------------------------------------'


def _should_show_command_form(datasource: ABCDataSource,
                              ignore_display_option: bool = False) -> bool:
    """Whether or not this view handles commands for the current user

    When it does not handle commands the command tab, command form, row
    selection and processing commands is disabled.
    """
    if not ignore_display_option and display_options.disabled(display_options.C):
        return False
    if not config.user.may("general.act"):
        return False

    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource.infos[0]
    for command_class in command_registry.values():
        command = command_class()
        if what in command.tables and config.user.may(command.permission.name):
            return True

    return False


def _get_command_groups(info_name: InfoName) -> Dict[Type[CommandGroup], List[Command]]:
    by_group: Dict[Type[CommandGroup], List[Command]] = {}

    for command_class in command_registry.values():
        command = command_class()
        if info_name in command.tables and config.user.may(command.permission.name):
            # Some special commands can be shown on special views using this option.  It is
            # currently only used by custom commands, not shipped with Checkmk.
            if command.only_view and html.request.var('view_name') != command.only_view:
                continue
            by_group.setdefault(command.group, []).append(command)

    return by_group


# Examine the current HTML variables in order determine, which
# command the user has selected. The fetch ids from a data row
# (host name, service description, downtime/commands id) and
# construct one or several core command lines and a descriptive
# title.
def core_command(what, row, row_nr, total_rows):
    host = row.get("host_name")
    descr = row.get("service_description")

    if what == "host":
        spec = host
        cmdtag = "HOST"
    elif what == "service":
        spec = "%s;%s" % (host, descr)
        cmdtag = "SVC"
    else:
        spec = row.get(what + "_id")
        if descr:
            cmdtag = "SVC"
        else:
            cmdtag = "HOST"

    commands, title = None, None
    # Call all command actions. The first one that detects
    # itself to be executed (by examining the HTML variables)
    # will return a command to execute and a title for the
    # confirmation dialog.
    for cmd_class in command_registry.values():
        cmd = cmd_class()
        if config.user.may(cmd.permission.name):
            result = cmd.action(cmdtag, spec, row, row_nr, total_rows)
            if result:
                executor = cmd.executor
                commands, title = result
                break

    if commands is None or title is None:
        raise MKUserError(None, _("Sorry. This command is not implemented."))

    # Some commands return lists of commands, others
    # just return one basic command. Convert those
    if not isinstance(commands, list):
        commands = [commands]

    return commands, title, executor


# Returns:
# True -> Actions have been done
# False -> No actions done because now rows selected
# [...] new rows -> Rows actions (shall/have) be performed on
def do_actions(view, what, action_rows, backurl):
    if not config.user.may("general.act"):
        html.show_error(
            _("You are not allowed to perform actions. "
              "If you think this is an error, please ask "
              "your administrator grant you the permission to do so."))
        return False  # no actions done

    if not action_rows:
        message_no_rows = _("No rows selected to perform actions for.")
        message_no_rows += '<br><a href="%s">%s</a>' % (backurl, _('Back to view'))
        html.show_error(message_no_rows)
        return False  # no actions done

    command = None
    title, executor = core_command(what, action_rows[0], 0,
                                   len(action_rows))[1:3]  # just get the title and executor
    if not confirm_with_preview(
            _("Do you really want to %(title)s the following %(count)d %(what)s?") % {
                "title": title,
                "count": len(action_rows),
                "what": visual_info_registry[what]().title_plural,
            },
            method='GET'):
        return False

    count = 0
    already_executed = set()
    for nr, row in enumerate(action_rows):
        core_commands, title, executor = core_command(what, row, nr, len(action_rows))
        for command_entry in core_commands:
            site = row.get(
                "site")  # site is missing for BI rows (aggregations can spawn several sites)
            if (site, command_entry) not in already_executed:
                # Some command functions return the information about the site per-command (e.g. for BI)
                if isinstance(command_entry, tuple):
                    site, command = command_entry
                else:
                    command = command_entry

                executor(command, site)
                already_executed.add((site, command_entry))
                count += 1

    message = None
    if command:
        message = _("Successfully sent %d commands.") % count
        if config.debug:
            message += _("The last one was: <pre>%s</pre>") % command
    elif count == 0:
        message = _("No matching data row. No command sent.")

    if message:
        backurl += "&filled_in=filter"
        message += '<br><a href="%s">%s</a>' % (backurl, _('Back to view'))
        if html.request.var("show_checkboxes") == "1":
            html.request.del_var("selection")
            weblib.selection_id()
            backurl += "&selection=" + html.request.get_str_input_mandatory("selection")
            message += '<br><a href="%s">%s</a>' % (backurl,
                                                    _('Back to view with checkboxes reset'))
        if html.request.var("_show_result") == "0":
            html.immediate_browser_redirect(0.5, backurl)
        html.show_message(message)

    return True


def filter_selected_rows(view, rows, selected_ids):
    action_rows = []
    for row in rows:
        if row_id(view, row) in selected_ids:
            action_rows.append(row)
    return action_rows


def get_context_link(user, viewname):
    if viewname in get_permitted_views():
        return "view.py?view_name=%s" % viewname
    return None


@cmk.gui.pages.register("export_views")
def ajax_export():
    for view in get_permitted_views().values():
        view["owner"] = ''
        view["public"] = True
    html.write(pprint.pformat(get_permitted_views()))


def get_view_by_name(view_name):
    return get_permitted_views()[view_name]


#.
#   .--Plugin Helpers------------------------------------------------------.
#   |   ____  _             _         _   _      _                         |
#   |  |  _ \| |_   _  __ _(_)_ __   | | | | ___| |_ __   ___ _ __ ___     |
#   |  | |_) | | | | |/ _` | | '_ \  | |_| |/ _ \ | '_ \ / _ \ '__/ __|    |
#   |  |  __/| | |_| | (_| | | | | | |  _  |  __/ | |_) |  __/ |  \__ \    |
#   |  |_|   |_|\__,_|\__, |_|_| |_| |_| |_|\___|_| .__/ \___|_|  |___/    |
#   |                 |___/                       |_|                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def register_hook(hook, func):
    if hook not in view_hooks:
        view_hooks[hook] = []

    if func not in view_hooks[hook]:
        view_hooks[hook].append(func)


def execute_hooks(hook):
    for hook_func in view_hooks.get(hook, []):
        try:
            hook_func()
        except Exception:
            if config.debug:
                raise MKGeneralException(
                    _('Problem while executing hook function %s in hook %s: %s') %
                    (hook_func.__name__, hook, traceback.format_exc()))


def docu_link(topic, text):
    return '<a href="%s" target="_blank">%s</a>' % (config.doculink_urlformat % topic, text)


#.
#   .--Icon Selector-------------------------------------------------------.
#   |      ___                  ____       _           _                   |
#   |     |_ _|___ ___  _ __   / ___|  ___| | ___  ___| |_ ___  _ __       |
#   |      | |/ __/ _ \| '_ \  \___ \ / _ \ |/ _ \/ __| __/ _ \| '__|      |
#   |      | | (_| (_) | | | |  ___) |  __/ |  __/ (__| || (_) | |         |
#   |     |___\___\___/|_| |_| |____/ \___|_|\___|\___|\__\___/|_|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | AJAX API call for rendering the icon selector                        |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("ajax_popup_icon_selector")
def ajax_popup_icon_selector():
    varprefix = html.request.var('varprefix')
    value = html.request.var('value')
    allow_empty = html.request.var('allow_empty') == '1'
    show_builtin_icons = html.request.var('show_builtin_icons') == '1'

    vs = IconSelector(allow_empty=allow_empty, show_builtin_icons=show_builtin_icons)
    vs.render_popup_input(varprefix, value)


#.
#   .--Action Menu---------------------------------------------------------.
#   |          _        _   _               __  __                         |
#   |         / \   ___| |_(_) ___  _ __   |  \/  | ___ _ __  _   _        |
#   |        / _ \ / __| __| |/ _ \| '_ \  | |\/| |/ _ \ '_ \| | | |       |
#   |       / ___ \ (__| |_| | (_) | | | | | |  | |  __/ | | | |_| |       |
#   |      /_/   \_\___|\__|_|\___/|_| |_| |_|  |_|\___|_| |_|\__,_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Realizes the popup action menu for hosts/services in views           |
#   '----------------------------------------------------------------------'


def query_action_data(what, host, site, svcdesc):
    # Now fetch the needed data from livestatus
    columns = list(iconpainter_columns(what, toplevel=False))
    try:
        columns.remove('site')
    except KeyError:
        pass

    query = livestatus_lql([host], columns, svcdesc)

    with sites.prepend_site(), sites.only_sites(site):
        row = sites.live().query_row(query)

    return dict(zip(['site'] + columns, row))


@cmk.gui.pages.register("ajax_popup_action_menu")
def ajax_popup_action_menu():
    site = html.request.var('site')
    host = html.request.var('host')
    svcdesc = html.request.get_unicode_input('service')
    what = 'service' if svcdesc else 'host'

    display_options.load_from_html()

    row = query_action_data(what, host, site, svcdesc)
    icons = get_icons(what, row, toplevel=False)

    html.open_ul()
    for icon in icons:
        if len(icon) != 4:
            html.open_li()
            html.write(icon[1])
            html.close_li()
        else:
            html.open_li()
            icon_name, title, url_spec = icon[1:]

            if url_spec:
                url, target_frame = transform_action_url(url_spec)
                url = replace_action_url_macros(url, what, row)
                onclick = None
                if url.startswith('onclick:'):
                    onclick = url[8:]
                    url = 'javascript:void(0);'
                html.open_a(href=url, target=target_frame, onclick=onclick)

            html.icon(icon_name)
            if title:
                html.write(title)
            else:
                html.write_text(_("No title"))
            if url_spec:
                html.close_a()
            html.close_li()
    html.close_ul()


#.
#   .--Reschedule----------------------------------------------------------.
#   |          ____                _              _       _                |
#   |         |  _ \ ___  ___  ___| |__   ___  __| |_   _| | ___           |
#   |         | |_) / _ \/ __|/ __| '_ \ / _ \/ _` | | | | |/ _ \          |
#   |         |  _ <  __/\__ \ (__| | | |  __/ (_| | |_| | |  __/          |
#   |         |_| \_\___||___/\___|_| |_|\___|\__,_|\__,_|_|\___|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Ajax webservice for reschedulung host- and service checks            |
#   '----------------------------------------------------------------------'


@page_registry.register_page("ajax_reschedule")
class PageRescheduleCheck(AjaxPage):
    """Is called to trigger a host / service check"""
    def page(self):
        request = html.get_request()
        return self._do_reschedule(request)

    def _do_reschedule(self, request):
        if not config.user.may("action.reschedule"):
            raise MKGeneralException("You are not allowed to reschedule checks.")

        site = request.get("site")
        host = request.get("host")
        if not host or not site:
            raise MKGeneralException("Action reschedule: missing host name")

        service = request.get("service", "")
        wait_svc = request.get("wait_svc", "")

        if service:
            cmd = "SVC"
            what = "service"
            spec = "%s;%s" % (host, service)

            if wait_svc:
                wait_spec = u'%s;%s' % (host, wait_svc)
                add_filter = "Filter: service_description = %s\n" % livestatus.lqencode(wait_svc)
            else:
                wait_spec = spec
                add_filter = "Filter: service_description = %s\n" % livestatus.lqencode(service)
        else:
            cmd = "HOST"
            what = "host"
            spec = host
            wait_spec = spec
            add_filter = ""

        now = int(time.time())
        sites.live().command(
            "[%d] SCHEDULE_FORCED_%s_CHECK;%s;%d" % (now, cmd, livestatus.lqencode(spec), now),
            site)

        query = u"GET %ss\n" \
                 "WaitObject: %s\n" \
                 "WaitCondition: last_check >= %d\n" \
                 "WaitTimeout: %d\n" \
                 "WaitTrigger: check\n" \
                 "Columns: last_check state plugin_output\n" \
                 "Filter: host_name = %s\n%s" \
                 % (what, livestatus.lqencode(wait_spec), now, config.reschedule_timeout * 1000, livestatus.lqencode(host), add_filter)
        with sites.only_sites(site):
            row = sites.live().query_row(query)

        last_check = row[0]
        if last_check < now:
            return {
                "state": "TIMEOUT",
                "message": _("Check not executed within %d seconds") % (config.reschedule_timeout),
            }

        if service == "Check_MK":
            # Passive services triggered by Check_MK often are updated
            # a few ms later. We introduce a small wait time in order
            # to increase the chance for the passive services already
            # updated also when we return.
            time.sleep(0.7)

        # Row is currently not used by the frontend, but may be useful for debugging
        return {
            "state": "OK",
            "row": row,
        }
