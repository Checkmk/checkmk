#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import ast
import collections
import functools
import json
import pprint
import time
from itertools import chain
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    overload,
    Sequence,
    Set,
)
from typing import Tuple as _Tuple
from typing import Type, Union

import livestatus
from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.prediction import livestatus_lql
from cmk.utils.site import omd_site
from cmk.utils.structured_data import StructuredDataNode
from cmk.utils.type_defs import HostName, ServiceName

import cmk.gui.forms as forms
import cmk.gui.i18n
import cmk.gui.log as log
import cmk.gui.pages
import cmk.gui.pagetypes as pagetypes
import cmk.gui.sites as sites
import cmk.gui.utils as utils
import cmk.gui.view_utils
import cmk.gui.visuals as visuals
import cmk.gui.weblib as weblib
from cmk.gui.bi import is_part_of_aggregation
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.config import active_config, builtin_role_ids, register_post_config_load_hook
from cmk.gui.ctx_stack import g
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import HTTPRedirect, MKGeneralException, MKInternalError, MKUserError
from cmk.gui.htmllib.context import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _u
from cmk.gui.inventory import (
    get_short_inventory_filepath,
    get_status_data_via_livestatus,
    load_filtered_and_merged_tree,
    load_latest_delta_tree,
    LoadStructuredDataError,
    parse_tree_path,
)
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import (
    make_checkbox_selection_topic,
    make_display_options_dropdown,
    make_external_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuPopup,
    PageMenuSidePopup,
    PageMenuTopic,
    toggle_page_menu_entries,
)
from cmk.gui.pages import AjaxPage, AjaxPageResult, page_registry
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    declare_permission,
    permission_section_registry,
    PermissionSection,
)

# Needed for legacy (pre 1.6) plugins
from cmk.gui.plugins.views.icons.utils import (  # noqa: F401  # pylint: disable=unused-import
    get_icons,
    get_multisite_icons,
    Icon,
    icon_and_action_registry,
    IconEntry,
    IconObjectType,
    iconpainter_columns,
    LegacyIconEntry,
    multisite_icons_and_actions,
)
from cmk.gui.plugins.views.perfometers.utils import (  # noqa: F401 # pylint: disable=unused-import
    perfometers,
)
from cmk.gui.plugins.views.utils import (  # noqa: F401 # pylint: disable=unused-import
    _parse_url_sorters,
    ABCDataSource,
    Cell,
    cmp_custom_variable,
    cmp_insensitive_string,
    cmp_ip_address,
    cmp_num_split,
    cmp_service_name_equiv,
    cmp_simple_number,
    cmp_simple_string,
    cmp_string_list,
    Command,
    command_registry,
    CommandExecutor,
    CommandGroup,
    CommandSpec,
    compare_ips,
    data_source_registry,
    declare_1to1_sorter,
    declare_simple_sorter,
    DerivedColumnsSorter,
    exporter_registry,
    format_plugin_output,
    get_all_views,
    get_custom_var,
    get_linked_visual_request_vars,
    get_perfdata_nth_value,
    get_permitted_views,
    get_tag_groups,
    get_view_infos,
    group_value,
    inventory_displayhints,
    is_stale,
    join_row,
    JoinCell,
    Layout,
    layout_registry,
    make_host_breadcrumb,
    make_linked_visual_url,
    make_service_breadcrumb,
    multisite_builtin_views,
    paint_age,
    paint_host_list,
    paint_stalified,
    Painter,
    painter_exists,
    painter_registry,
    PainterOptions,
    PainterRegistry,
    register_command_group,
    register_legacy_command,
    register_painter,
    register_sorter,
    replace_action_url_macros,
    row_id,
    Sorter,
    sorter_registry,
    SorterEntry,
    SorterListEntry,
    SorterRegistry,
    SorterSpec,
    transform_action_url,
    view_hooks,
    view_is_enabled,
    view_title,
)
from cmk.gui.plugins.visuals.utils import (
    Filter,
    get_livestatus_filter_headers,
    visual_info_registry,
    visual_type_registry,
    VisualInfo,
    VisualType,
)

# Needed for legacy (pre 1.6) plugins
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    CascadingDropdownChoice,
    Dictionary,
    DropdownChoice,
    DropdownChoiceEntries,
    DropdownChoiceEntry,
    FixedValue,
    Hostname,
    IconSelector,
    Integer,
    ListChoice,
    ListOf,
    TextInput,
    Transform,
    Tuple,
    ValueSpec,
)
from cmk.gui.view_utils import get_labels, render_labels, render_tag_groups
from cmk.gui.views.builtin_views import builtin_views
from cmk.gui.views.inventory import declare_inventory_columns, declare_invtable_views
from cmk.gui.watolib.activate_changes import get_pending_changes_info, get_pending_changes_tooltip

if not cmk_version.is_raw_edition():
    from cmk.gui.cee.ntop.connector import get_cache  # pylint: disable=no-name-in-module

from cmk.gui.type_defs import (
    ColumnName,
    FilterName,
    HTTPVariables,
    InfoName,
    PainterSpec,
    Perfdata,
    PerfometerSpec,
    Row,
    Rows,
    SingleInfos,
    TranslatedMetrics,
    ViewName,
    ViewProcessTracking,
    ViewSpec,
    Visual,
    VisualContext,
)
from cmk.gui.utils.confirm_with_preview import confirm_with_preview
from cmk.gui.utils.ntop import get_ntop_connection, is_ntop_configured
from cmk.gui.utils.urls import makeuri, makeuri_contextless

from . import availability

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
        result = super().link_from(linking_view, linking_view_rows, visual, context_vars)
        if result is False:
            return False

        link_from = visual["link_from"]
        if not link_from:
            return True  # No link from filtering: Always display this.

        inventory_tree_condition = link_from.get("has_inventory_tree")
        if inventory_tree_condition and not _has_inventory_tree(
            linking_view, linking_view_rows, visual, context_vars, inventory_tree_condition
        ):
            return False

        inventory_tree_history_condition = link_from.get("has_inventory_tree_history")
        if inventory_tree_history_condition and not _has_inventory_tree(
            linking_view,
            linking_view_rows,
            visual,
            context_vars,
            inventory_tree_history_condition,
            is_history=True,
        ):
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
    except LoadStructuredDataError:
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
    parsed_path, _attribute_keys = parse_tree_path(invpath)
    if (node := struct_tree.get_node(parsed_path)) is None or node.is_empty():
        return False
    return True


def _get_struct_tree(is_history, hostname, site_id):
    struct_tree_cache = g.setdefault("struct_tree_cache", {})
    cache_id = (is_history, hostname, site_id)
    if cache_id in struct_tree_cache:
        return struct_tree_cache[cache_id]

    if is_history:
        struct_tree = load_latest_delta_tree(hostname)
    else:
        row = get_status_data_via_livestatus(site_id, hostname)
        struct_tree = load_filtered_and_merged_tree(row)

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

    def __init__(self, view_name: str, view_spec: ViewSpec, context: VisualContext) -> None:
        super().__init__()
        self.name = view_name
        self.spec = view_spec
        self.context: VisualContext = context
        self._row_limit: Optional[int] = None
        self._only_sites: Optional[List[SiteId]] = None
        self._user_sorters: Optional[List[SorterSpec]] = None
        self._want_checkboxes: bool = False
        self.process_tracking = ViewProcessTracking()

    @property
    def datasource(self) -> ABCDataSource:
        try:
            return data_source_registry[self.spec["datasource"]]()
        except KeyError:
            if self.spec["datasource"].startswith("mkeventd_"):
                raise MKUserError(
                    None,
                    _(
                        "The Event Console view '%s' can not be rendered. The Event Console is possibly "
                        "disabled."
                    )
                    % self.name,
                )
            raise MKUserError(
                None,
                _(
                    "The view '%s' using the datasource '%s' can not be rendered "
                    "because the datasource does not exist."
                )
                % (self.name, self.datasource),
            )

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
            self.user_sorters if self.user_sorters else self.spec["sorters"]
        )

    # TODO: make sure sorter_list type is correct
    def _get_sorter_entries(self, sorter_list: List[SorterListEntry]) -> List[SorterEntry]:
        sorters: List[SorterEntry] = []
        for entry in sorter_list:
            sorter_name: Union[str, _Tuple[str, Dict[str, str]]] = entry[0]
            negate: bool = entry[1]
            join_key: Optional[str] = None
            if len(entry) == 3:
                # mypy can not understand the if statement:
                # https://github.com/python/mypy/issues/1178
                # https://github.com/python/mypy/issues/7509
                # so we use an ugly cast,..
                join_key = cast(List[Optional[str]], entry)[2]

            uuid = None
            if isinstance(sorter_name, tuple):
                sorter_name, parameters = sorter_name
                if sorter_name not in {"host_custom_variable"}:
                    raise MKGeneralException(
                        f"Don't know how to proceed with sorter {sorter_name} parameters {parameters}"
                    )
                uuid = parameters["ident"]
            elif ":" in sorter_name:
                sorter_name, uuid = sorter_name.split(":", 1)

            sorter = sorter_registry.get(sorter_name, None)

            if sorter is None:
                continue  # Skip removed sorters

            sorter_instance = sorter()
            if isinstance(sorter_instance, DerivedColumnsSorter):
                sorter_instance.derived_columns(self, uuid)

            sorters.append(SorterEntry(sorter=sorter_instance, negate=negate, join_key=join_key))
        return sorters

    @property
    def row_limit(self):
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

    # FIXME: The layout should get the view as a parameter by default.
    @property
    def layout(self) -> Layout:
        """Return the HTML layout of the view"""
        if "layout" in self.spec:
            return layout_registry[self.spec["layout"]]()

        raise MKUserError(
            None,
            _(
                "The view '%s' using the layout '%s' can not be rendered "
                "because the layout does not exist."
            )
            % (self.name, self.spec.get("layout")),
        )

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
        return self.layout.can_display_checkboxes and (
            self.checkboxes_enforced or self.want_checkboxes
        )

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
        if "host" not in self.spec["single_infos"] or "host" in self.missing_single_infos:
            request_vars: HTTPVariables = [("view_name", self.name)]
            request_vars += list(
                visuals.get_singlecontext_vars(self.context, self.spec["single_infos"]).items()
            )

            breadcrumb = make_topic_breadcrumb(
                mega_menu_registry.menu_monitoring(),
                pagetypes.PagetypeTopics.get_topic(self.spec["topic"]).title(),
            )
            breadcrumb.append(
                BreadcrumbItem(
                    title=view_title(self.spec, self.context),
                    url=makeuri_contextless(request, request_vars),
                )
            )
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
        host_name = self.context["host"]["host"]
        breadcrumb = make_host_breadcrumb(HostName(host_name))

        if self.name == "host":
            # In case we are on the host homepage, we have the final breadcrumb
            return breadcrumb

        # 3a) level: other single host pages
        if "service" not in self.spec["single_infos"]:
            # All other single host pages are right below the host home page
            breadcrumb.append(
                BreadcrumbItem(
                    title=view_title(self.spec, self.context),
                    url=makeuri_contextless(
                        request,
                        [("view_name", self.name), ("host", host_name)],
                    ),
                )
            )
            return breadcrumb

        breadcrumb = make_service_breadcrumb(
            HostName(host_name), ServiceName(self.context["service"]["service"])
        )

        if self.name == "service":
            # In case we are on the service home page, we have the final breadcrumb
            return breadcrumb

        # All other single service pages are right below the host home page
        breadcrumb.append(
            BreadcrumbItem(
                title=view_title(self.spec, self.context),
                url=makeuri_contextless(
                    request,
                    [
                        ("view_name", self.name),
                        ("host", host_name),
                        ("service", self.context["service"]["service"]),
                    ],
                ),
            )
        )

        return breadcrumb

    @property
    def missing_single_infos(self) -> Set[FilterName]:
        """Return the missing single infos a view requires"""
        missing_single_infos = visuals.get_missing_single_infos(
            self.spec["single_infos"], self.context
        )

        # Special hack for the situation where host group views link to host views: The host view uses
        # the datasource "hosts" which does not have the "hostgroup" info, but is configured to have a
        # single_info "hostgroup". To make this possible there exists a feature in
        # (ABCDataSource.link_filters, views._patch_view_context) which is a very specific hack. Have a
        # look at the description there.  We workaround the issue here by allowing this specific
        # situation but validating all others.
        #
        # The more correct approach would be to find a way which allows filters of different datasources
        # to have equal names. But this would need a bigger refactoring of the filter mechanic. One
        # day...
        if (
            self.spec["datasource"] in ["hosts", "services"]
            and missing_single_infos == {"hostgroup"}
            and "opthostgroup" in self.context
        ):
            return set()
        if (
            self.spec["datasource"] == "services"
            and missing_single_infos == {"servicegroup"}
            and "optservicegroup" in self.context
        ):
            return set()

        return missing_single_infos


class DummyView(View):
    """Represents an empty view hull, not intended to be displayed
    This view can be used as surrogate where a view-ish like object is needed
    """

    def __init__(self):
        super().__init__("dummy_view", {}, {})


class ABCViewRenderer(abc.ABC):
    def __init__(self, view: View) -> None:
        super().__init__()
        self.view = view
        self._menu_topics: Dict[str, List[PageMenuTopic]] = collections.defaultdict(list)

    def append_menu_topic(self, dropdown: str, topic: PageMenuTopic) -> None:
        self._menu_topics[dropdown].append(topic)

    @abc.abstractmethod
    def render(
        self,
        rows: Rows,
        show_checkboxes: bool,
        num_columns: int,
        show_filters: List[Filter],
        unfiltered_amount_of_rows: int,
    ):
        raise NotImplementedError()


class GUIViewRenderer(ABCViewRenderer):
    def __init__(self, view: View, show_buttons: bool) -> None:
        super().__init__(view)
        self._show_buttons = show_buttons

    def render(
        self,
        rows: Rows,
        show_checkboxes: bool,
        num_columns: int,
        show_filters: List[Filter],
        unfiltered_amount_of_rows: int,
    ):
        view_spec = self.view.spec

        if transactions.transaction_valid() and html.do_actions():
            html.set_browser_reload(0)

        # Show/Hide the header with page title, MK logo, etc.
        if display_options.enabled(display_options.H):
            html.body_start(view_title(view_spec, self.view.context))

        if display_options.enabled(display_options.T):
            if self.view.checkboxes_displayed:
                weblib.selection_id()
            breadcrumb = self.view.breadcrumb()
            html.top_heading(
                view_title(view_spec, self.view.context),
                breadcrumb,
                page_menu=self._page_menu(rows, show_filters),
            )
            html.begin_page_content()

        has_done_actions = False
        row_count = len(rows)

        command_form = _should_show_command_form(self.view.datasource)
        if command_form:
            weblib.init_selection()

        # Used this before. This does not looked like it's correct, replaced the logic
        # enable_commands = painter_options.painter_option_form_enabled()
        # enable_checkboxes = view.layout.can_display_checkboxes and not checkboxes_enforced
        # selection_enabled = enable_checkboxes if enable_commands else checkboxes_enforced
        html.javascript(
            "cmk.selection.set_selection_enabled(%s);" % json.dumps(self.view.checkboxes_displayed)
        )

        layout = self.view.layout

        # Display the filter form on page rendering in some cases
        if self._should_show_filter_form():
            html.final_javascript("cmk.page_menu.open_popup('popup_filters');")

        # Actions
        if command_form:
            # There are one shot actions which only want to affect one row, filter the rows
            # by this id during actions
            if request.has_var("_row_id") and html.do_actions():
                rows = _filter_selected_rows(
                    view_spec, rows, [request.get_str_input_mandatory("_row_id")]
                )

            # If we are currently within an action (confirming or executing), then
            # we display only the selected rows (if checkbox mode is active)
            elif show_checkboxes and html.do_actions():
                rows = _filter_selected_rows(
                    view_spec,
                    rows,
                    user.get_rowselection(weblib.selection_id(), "view-" + view_spec["name"]),
                )

            if (
                html.do_actions() and transactions.transaction_valid()
            ):  # submit button pressed, no reload
                try:
                    # Create URI with all actions variables removed
                    backurl = makeuri(request, [], delvars=["filled_in", "actions"])
                    has_done_actions = do_actions(
                        view_spec, self.view.datasource.infos[0], rows, backurl
                    )
                except MKUserError as e:
                    html.user_error(e)

        # Also execute commands in cases without command form (needed for Python-
        # web service e.g. for NagStaMon)
        elif (
            row_count > 0
            and user.may("general.act")
            and html.do_actions()
            and transactions.transaction_valid()
        ):

            # There are one shot actions which only want to affect one row, filter the rows
            # by this id during actions
            if request.has_var("_row_id") and html.do_actions():
                rows = _filter_selected_rows(
                    view_spec, rows, [request.get_str_input_mandatory("_row_id")]
                )

            try:
                do_actions(view_spec, self.view.datasource.infos[0], rows, "")
            except Exception:
                pass  # currently no feed back on webservice

        # The refreshing content container
        if display_options.enabled(display_options.R):
            html.open_div(id_="data_container")

        missing_single_infos = self.view.missing_single_infos
        if missing_single_infos:
            html.show_warning(
                _(
                    "Unable to render this view, "
                    "because we miss some required context information (%s). Please update the "
                    "form on the right to make this view render."
                )
                % ", ".join(sorted(missing_single_infos))
            )

        if not has_done_actions and not missing_single_infos:
            html.div("", id_="row_info")
            if display_options.enabled(display_options.W):
                row_limit = None if self.view.datasource.ignore_limit else self.view.row_limit
                if cmk.gui.view_utils.row_limit_exceeded(
                    unfiltered_amount_of_rows,
                    row_limit,
                ) or cmk.gui.view_utils.row_limit_exceeded(
                    len(rows),
                    row_limit,
                ):
                    cmk.gui.view_utils.query_limit_exceeded_warn(row_limit, user)
                    del rows[row_limit:]
                    self.view.process_tracking.amount_rows_after_limit = len(rows)

            layout.render(
                rows,
                view_spec,
                self.view.group_cells,
                self.view.row_cells,
                num_columns,
                show_checkboxes and not html.do_actions(),
            )
            row_info = "%d %s" % (row_count, _("row") if row_count == 1 else _("rows"))
            if show_checkboxes:
                selected = _filter_selected_rows(
                    view_spec,
                    rows,
                    user.get_rowselection(weblib.selection_id(), "view-" + view_spec["name"]),
                )
                row_info = "%d/%s" % (len(selected), row_info)
            html.javascript("cmk.utils.update_row_info(%s);" % json.dumps(row_info))

            # The number of rows might have changed to enable/disable actions and checkboxes
            if self._show_buttons:
                # don't take display_options into account here ('c' is set during reload)
                toggle_page_menu_entries(
                    css_class="command",
                    state=row_count > 0
                    and _should_show_command_form(self.view.datasource, ignore_display_option=True),
                )

            # Play alarm sounds, if critical events have been displayed
            if display_options.enabled(display_options.S) and view_spec.get("play_sounds"):
                play_alarm_sounds()
        else:
            # Always hide action related context links in this situation
            toggle_page_menu_entries(css_class="command", state=False)

        # In multi site setups error messages of single sites do not block the
        # output and raise now exception. We simply print error messages here.
        # In case of the web service we show errors only on single site installations.
        if active_config.show_livestatus_errors and display_options.enabled(display_options.W):
            for info in sites.live().dead_sites().values():
                if isinstance(info["site"], dict):
                    html.show_error(
                        "<b>%s - %s</b><br>%s"
                        % (info["site"]["alias"], _("Livestatus error"), info["exception"])
                    )

        if display_options.enabled(display_options.R):
            html.close_div()

        if display_options.enabled(display_options.T):
            html.end_page_content()

        if display_options.enabled(display_options.H):
            html.body_end()

    def _should_show_filter_form(self) -> bool:
        """Whether or not the filter form should be displayed on page load

        a) In case the user toggled the popup in the frontend, always enforce that property

        b) Show in case the view is a "mustsearch" view (User needs to submit the filter form before
        data is shown).

        c) Show after submitting the filter form. The user probably wants to update the filters
        after first filtering.

        d) In case there are single info filters missing
        """

        show_form = request.get_integer_input("_show_filter_form")
        if show_form is not None:
            return show_form == 1

        if self.view.spec.get("mustsearch"):
            return True

        if request.get_ascii_input("filled_in") == "filter":
            return True

        if self.view.missing_single_infos:
            return True

        return False

    def _page_menu(self, rows: Rows, show_filters: List[Filter]) -> PageMenu:
        breadcrumb: Breadcrumb = self.view.breadcrumb()
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

        page_menu_dropdowns = (
            self._page_menu_dropdown_commands()
            + self._page_menu_dropdowns_context(rows)
            + self._page_menu_dropdown_add_to()
            + export_dropdown
        )

        if rows:
            host_address = rows[0].get("host_address")
            if is_ntop_configured():
                ntop_connection = get_ntop_connection()
                assert ntop_connection
                ntop_instance = ntop_connection["hostaddress"]
                if (
                    host_address is not None
                    and get_cache().is_instance_up(ntop_instance)
                    and get_cache().is_ntop_host(host_address)
                ):
                    page_menu_dropdowns.insert(3, self._page_menu_dropdowns_ntop(host_address))

        menu = PageMenu(
            dropdowns=page_menu_dropdowns,
            breadcrumb=breadcrumb,
            has_pending_changes=bool(get_pending_changes_info()),
            pending_changes_tooltip=get_pending_changes_tooltip(),
        )

        self._extend_display_dropdown(menu, show_filters)
        self._extend_help_dropdown(menu)

        for dropdown_name, topics in self._menu_topics.items():
            menu[dropdown_name].topics.extend(topics)

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
                    make_checkbox_selection_topic(
                        "view-%s" % self.view.spec["name"],
                        is_enabled=self.view.checkboxes_displayed,
                    ),
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

    def _page_menu_dropdowns_ntop(self, host_address) -> PageMenuDropdown:
        return _get_ntop_page_menu_dropdown(self.view, host_address)

    def _page_menu_entries_export_data(self) -> Iterator[PageMenuEntry]:
        if not user.may("general.csv_export"):
            return

        yield PageMenuEntry(
            title=_("Export CSV"),
            icon_name="download_csv",
            item=make_simple_link(
                makeuri(
                    request,
                    [("output_format", "csv_export")],
                    delvars=["show_checkboxes", "selection"],
                )
            ),
        )

        yield PageMenuEntry(
            title=_("Export JSON"),
            icon_name="download_json",
            item=make_simple_link(
                makeuri(
                    request,
                    [("output_format", "json_export")],
                    delvars=["show_checkboxes", "selection"],
                )
            ),
        )

    def _page_menu_entries_export_reporting(self, rows: Rows) -> Iterator[PageMenuEntry]:
        if cmk_version.is_raw_edition():
            return

        if not user.may("general.instant_reports"):
            return

        yield PageMenuEntry(
            title=_("This view as PDF"),
            icon_name="report",
            item=make_simple_link(
                makeuri(
                    request,
                    [],
                    filename="report_instant.py",
                    delvars=["show_checkboxes", "selection"],
                )
            ),
            css_classes=["context_pdf_export"],
        )

        # Link related reports
        yield from collect_context_links(self.view, rows, mobile=False, visual_types=["reports"])

    def _extend_display_dropdown(self, menu: PageMenu, show_filters: List[Filter]) -> None:
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())

        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("View layout"),
                entries=list(self._page_menu_entries_view_layout()),
            ),
        )

        if display_options.enabled(display_options.D):
            display_dropdown.topics.insert(
                0,
                PageMenuTopic(
                    title=_("Format"),
                    entries=list(self._page_menu_entries_view_format()),
                ),
            )

        if display_options.enabled(display_options.F):
            display_dropdown.topics.insert(
                0,
                PageMenuTopic(
                    title=_("Filter"),
                    entries=list(self._page_menu_entries_filter(show_filters)),
                ),
            )

    def _page_menu_entries_filter(self, show_filters: List[Filter]) -> Iterator[PageMenuEntry]:
        is_filter_set = request.var("filled_in") == "filter"

        yield PageMenuEntry(
            title=_("Filter"),
            icon_name="filters_set" if is_filter_set else "filter",
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
        checkboxes_toggleable = (
            self.view.layout.can_display_checkboxes and not self.view.checkboxes_enforced
        )
        yield PageMenuEntry(
            title=_("Show checkboxes"),
            icon_name="checked_checkbox" if self.view.checkboxes_displayed else "checkbox",
            item=make_simple_link(
                makeuri(
                    request,
                    [
                        ("show_checkboxes", "0" if self.view.checkboxes_displayed else "1"),
                    ],
                )
            ),
            is_shortcut=True,
            is_suggested=True,
            is_enabled=checkboxes_toggleable,
        )

        if display_options.enabled(display_options.E) and user.may("general.edit_views"):
            url_vars: HTTPVariables = [
                ("back", request.requested_url),
                ("load_name", self.view.name),
            ]

            clone_mode: bool = False
            if self.view.spec["owner"] != user.id:
                url_vars.append(("owner", self.view.spec["owner"]))
                if not user.may("general.edit_foreign_views"):
                    clone_mode = True

            url_vars.append(("mode", "clone" if clone_mode else "edit"))
            url = makeuri_contextless(request, url_vars, filename="edit_view.py")

            yield PageMenuEntry(
                title=_("Clone view") if clone_mode else _("Customize view"),
                icon_name="clone" if clone_mode else "edit",
                item=make_simple_link(url),
            )

    def _page_menu_dropdown_add_to(self) -> List[PageMenuDropdown]:
        return visuals.page_menu_dropdown_add_to_visual(add_type="view", name=self.view.name)

    def _render_filter_form(self, show_filters: List[Filter]) -> HTML:
        if not display_options.enabled(display_options.F) or not show_filters:
            return HTML()

        with output_funnel.plugged():
            show_filter_form(self.view, show_filters)
            return HTML(output_funnel.drain())

    def _render_painter_options_form(self) -> HTML:
        with output_funnel.plugged():
            painter_options = PainterOptions.get_instance()
            painter_options.show_form(self.view)
            return HTML(output_funnel.drain())

    def _render_command_form(self, info_name: InfoName, command: Command) -> HTML:
        with output_funnel.plugged():
            if not _should_show_command_form(self.view.datasource):
                return HTML()

            # TODO: Make unique form names (object IDs), investigate whether or not something
            # depends on the form name "actions"
            html.begin_form("actions")
            # TODO: Are these variables still needed
            html.hidden_field("_do_actions", "yes")
            html.hidden_field("actions", "yes")

            command.render(info_name)

            html.hidden_fields()
            html.end_form()

            return HTML(output_funnel.drain())

    def _extend_help_dropdown(self, menu: PageMenu) -> None:
        # TODO
        # menu.add_doc_reference(title=_("Host administration"), doc_ref=DocReference.WATO_HOSTS)
        # menu.add_youtube_reference(title=_("Episode 4: Monitoring Windows in Checkmk"),
        #                           youtube_id="Nxiq7Jb9mB4")
        pass


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("views", globals())
    utils.load_web_plugins("icons", globals())
    utils.load_web_plugins("perfometer", globals())

    transform_old_dict_based_icons()

    # TODO: Kept for compatibility with pre 1.6 plugins. Plugins will not be used anymore, but an error
    # will be displayed.
    if multisite_painter_options:
        raise MKGeneralException(
            "Found legacy painter option plugins: %s. You will either have to "
            "remove or migrate them." % ", ".join(multisite_painter_options.keys())
        )
    if multisite_layouts:
        raise MKGeneralException(
            "Found legacy layout plugins: %s. You will either have to "
            "remove or migrate them." % ", ".join(multisite_layouts.keys())
        )
    if multisite_datasources:
        raise MKGeneralException(
            "Found legacy data source plugins: %s. You will either have to "
            "remove or migrate them." % ", ".join(multisite_datasources.keys())
        )

    # TODO: Kept for compatibility with pre 1.6 plugins
    for cmd_spec in multisite_commands:
        register_legacy_command(cmd_spec)

    multisite_builtin_views.update(builtin_views)

    # Needs to be executed after all plugins (builtin and local) are loaded
    declare_inventory_columns()
    declare_invtable_views()

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_painters.items():
        register_painter(ident, spec)

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_sorters.items():
        register_sorter(ident, spec)

    visuals.declare_visual_permissions("views", _("views"))

    # Declare permissions for builtin views
    for name, view_spec in multisite_builtin_views.items():
        declare_permission(
            "view.%s" % name,
            format_view_title(name, view_spec),
            "%s - %s" % (name, _u(view_spec["description"])),
            builtin_role_ids,
        )

    # Make sure that custom views also have permissions
    declare_dynamic_permissions(lambda: visuals.declare_custom_permissions("views"))


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.
    """
    # Needs to be a local import to not influence the regular plugin loading order
    import cmk.gui.plugins.views as api_module  # pylint: disable=cmk-module-layer-violation
    import cmk.gui.plugins.views.utils as plugin_utils

    for name in (
        "ABCDataSource",
        "Cell",
        "CellSpec",
        "cmp_custom_variable",
        "cmp_ip_address",
        "cmp_num_split",
        "cmp_service_name_equiv",
        "cmp_simple_number",
        "cmp_simple_string",
        "cmp_string_list",
        "Command",
        "command_group_registry",
        "command_registry",
        "CommandActionResult",
        "CommandGroup",
        "CommandSpec",
        "compare_ips",
        "data_source_registry",
        "DataSourceLivestatus",
        "declare_1to1_sorter",
        "declare_simple_sorter",
        "DerivedColumnsSorter",
        "display_options",
        "EmptyCell",
        "ExportCellContent",
        "Exporter",
        "exporter_registry",
        "format_plugin_output",
        "get_graph_timerange_from_painter_options",
        "get_label_sources",
        "get_perfdata_nth_value",
        "get_permitted_views",
        "get_tag_groups",
        "group_value",
        "inventory_displayhints",
        "InventoryHintSpec",
        "is_stale",
        "join_row",
        "Layout",
        "layout_registry",
        "multisite_builtin_views",
        "output_csv_headers",
        "paint_age",
        "paint_host_list",
        "paint_nagiosflag",
        "paint_stalified",
        "Painter",
        "painter_option_registry",
        "painter_registry",
        "PainterOption",
        "PainterOptions",
        "query_livestatus",
        "register_painter",
        "register_sorter",
        "render_cache_info",
        "render_link_to_view",
        "replace_action_url_macros",
        "Row",
        "row_id",
        "RowTable",
        "RowTableLivestatus",
        "Sorter",
        "sorter_registry",
        "transform_action_url",
        "url_to_visual",
        "view_is_enabled",
        "view_title",
        "VisualLinkSpec",
    ):
        api_module.__dict__[name] = plugin_utils.__dict__[name]

    api_module.__dict__.update(
        {
            "Perfdata": Perfdata,
            "PerfometerSpec": PerfometerSpec,
            "TranslatedMetrics": TranslatedMetrics,
            "get_labels": get_labels,
            "render_labels": render_labels,
            "render_tag_groups": render_tag_groups,
        }
    )


# Transform pre 1.6 icon plugins. Deprecate this one day.
def transform_old_dict_based_icons():
    for icon_id, icon in multisite_icons_and_actions.items():
        icon_class = type(
            "LegacyIcon%s" % icon_id.title(),
            (Icon,),
            {
                "_ident": icon_id,
                "_icon_spec": icon,
                "ident": classmethod(lambda cls: cls._ident),
                "title": classmethod(lambda cls: cls._title),
                "sort_index": lambda self: self._icon_spec.get("sort_index", 30),
                "toplevel": lambda self: self._icon_spec.get("toplevel", False),
                "render": lambda self, *args: self._icon_spec["paint"](*args),
                "columns": lambda self: self._icon_spec.get("columns", []),
                "host_columns": lambda self: self._icon_spec.get("host_columns", []),
                "service_columns": lambda self: self._icon_spec.get("service_columns", []),
            },
        )

        icon_and_action_registry.register(icon_class)


def _register_tag_plugins():
    if getattr(_register_tag_plugins, "_config_hash", None) == _calc_config_hash():
        return  # No re-register needed :-)
    _register_host_tag_painters()
    _register_host_tag_sorters()
    setattr(_register_tag_plugins, "_config_hash", _calc_config_hash())


def _calc_config_hash() -> int:
    return hash(repr(active_config.tags.get_dict_format()))


register_post_config_load_hook(_register_tag_plugins)


def _register_host_tag_painters():
    # first remove all old painters to reflect delted painters during runtime
    for key in list(painter_registry.keys()):
        if key.startswith("host_tag_"):
            painter_registry.unregister(key)

    for tag_group in active_config.tags.tag_groups:
        if tag_group.topic:
            long_title = tag_group.topic + " / " + tag_group.title
        else:
            long_title = tag_group.title

        ident = "host_tag_" + tag_group.id
        spec = {
            "title": _("Host tag:") + " " + long_title,
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
            },
        )
        painter_registry.register(cls)


def _paint_host_tag(row, tgid):
    return "", _get_tag_group_value(row, "host", tgid)


def _register_host_tag_sorters():
    for tag_group in active_config.tags.tag_groups:
        register_sorter(
            "host_tag_" + str(tag_group.id),
            {
                "_tag_group_id": tag_group.id,
                "title": _("Host tag:") + " " + tag_group.title,
                "columns": ["host_tags"],
                "cmp": lambda self, r1, r2: _cmp_host_tag(r1, r2, self._spec["_tag_group_id"]),
            },
        )


def _cmp_host_tag(r1, r2, tgid):
    host_tag_1 = _get_tag_group_value(r1, "host", tgid)
    host_tag_2 = _get_tag_group_value(r2, "host", tgid)
    return (host_tag_1 > host_tag_2) - (host_tag_1 < host_tag_2)


def _get_tag_group_value(row, what, tag_group_id) -> str:
    tag_id = get_tag_groups(row, "host").get(tag_group_id)

    tag_group = active_config.tags.get_tag_group(tag_group_id)
    if tag_group:
        label = dict(tag_group.get_tag_choices()).get(tag_id, _("N/A"))
    else:
        label = tag_id or _("N/A")

    return label or _("N/A")


# .
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
    cols = [(_("Datasource"), lambda v: data_source_registry[v["datasource"]]().title)]
    visuals.page_list("views", _("Edit Views"), get_all_views(), cols)


# .
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
        title=_("Datasource"),
        help=_("The datasources define which type of objects should be displayed with this view."),
        choices=data_source_registry.data_source_choices(),
        default_value="services",
    )


@cmk.gui.pages.register("create_view")
def page_create_view():
    show_create_view_dialog()


def show_create_view_dialog(next_url=None):
    vs_ds = DatasourceSelection()

    ds = "services"  # Default selection

    title = _("Create view")
    breadcrumb = visuals.visual_page_breadcrumb("views", title, "create")
    html.header(
        title,
        breadcrumb,
        make_simple_form_page_menu(
            _("View"),
            breadcrumb,
            form_name="create_view",
            button_name="_save",
            save_title=_("Continue"),
        ),
    )

    if request.var("_save") and transactions.check_transaction():
        try:
            ds = vs_ds.from_html_vars("ds")
            vs_ds.validate_value(ds, "ds")

            if not next_url:
                next_url = makeuri(
                    request,
                    [("datasource", ds)],
                    filename="create_view_infos.py",
                )
            else:
                next_url = next_url + "&datasource=%s" % ds
            raise HTTPRedirect(next_url)
        except MKUserError as e:
            html.user_error(e)

    html.begin_form("create_view")
    html.hidden_field("mode", "create")

    forms.header(_("Select Datasource"))
    forms.section(vs_ds.title())
    vs_ds.render_input("ds", ds)
    html.help(vs_ds.help())
    forms.end()

    html.hidden_fields()
    html.end_form()
    html.footer()


@cmk.gui.pages.register("create_view_infos")
def page_create_view_infos():
    ds_class, ds_name = request.get_item_input("datasource", data_source_registry)
    visuals.page_create_visual(
        "views",
        ds_class().infos,
        next_url="edit_view.py?mode=create&datasource=%s&single_infos=%%s" % ds_name,
    )


# .
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
        "views",
        get_all_views(),
        custom_field_handler=render_view_config,
        load_handler=transform_view_to_valuespec_value,
        create_handler=create_view_from_valuespec,
        info_handler=get_view_infos,
    )


def view_choices(only_with_hidden=False, allow_empty=True):
    choices = []
    if allow_empty:
        choices.append(("", ""))
    for name, view in get_permitted_views().items():
        if not only_with_hidden or view["single_infos"]:
            title = format_view_title(name, view)
            choices.append(("%s" % name, title))
    return choices


def format_view_title(name, view):
    title_parts = []

    if view.get("mobile", False):
        title_parts.append(_("Mobile"))

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
        title_parts.append(_("Host groups"))
    elif "servicegroup" in infos:
        title_parts.append(_("Service groups"))

    title_parts.append("%s (%s)" % (_u(view["title"]), name))

    return " - ".join(map(str, title_parts))


def view_editor_options():
    return [
        ("mobile", _("Show this view in the Mobile GUI")),
        ("mustsearch", _("Show data only on search")),
        ("force_checkboxes", _("Always show the checkboxes")),
        ("user_sortable", _("Make view sortable by user")),
        ("play_sounds", _("Play alarm sounds")),
    ]


def view_editor_general_properties(ds_name):
    return Dictionary(
        title=_("View Properties"),
        render="form",
        optional_keys=False,
        elements=[
            (
                "datasource",
                FixedValue(
                    value=ds_name,
                    title=_("Datasource"),
                    totext=data_source_registry[ds_name]().title,
                    help=_("The datasource of a view cannot be changed."),
                ),
            ),
            (
                "options",
                ListChoice(
                    title=_("Options"),
                    choices=view_editor_options(),
                    default_value=["user_sortable"],
                ),
            ),
            (
                "browser_reload",
                Integer(
                    title=_("Automatic page reload"),
                    unit=_("seconds"),
                    minvalue=0,
                    help=_('Set to "0" to disable the automatic reload.'),
                ),
            ),
            (
                "layout",
                DropdownChoice(
                    title=_("Basic Layout"),
                    choices=layout_registry.get_choices(),
                    default_value="table",
                    sorted=True,
                ),
            ),
            (
                "num_columns",
                Integer(
                    title=_("Number of Columns"),
                    default_value=1,
                    minvalue=1,
                    maxvalue=50,
                ),
            ),
            (
                "column_headers",
                DropdownChoice(
                    title=_("Column Headers"),
                    choices=[
                        ("off", _("off")),
                        ("pergroup", _("once per group")),
                        ("repeat", _("repeat every 20'th row")),
                    ],
                    default_value="pergroup",
                ),
            ),
        ],
    )


def view_editor_column_spec(ident, title, ds_name):

    allow_empty = True
    empty_text = None
    if ident == "columns":
        allow_empty = False
        empty_text = _("Please add at least one column to your view.")

    def column_elements(_painters, painter_type):
        empty_choices: DropdownChoiceEntries = [(None, "")]
        elements = [
            CascadingDropdown(
                title=_("Column"),
                choices=painter_choices_with_params(_painters),
                no_preselect_title="",
                render_sub_vs_page_name="ajax_cascading_render_painer_parameters",
                render_sub_vs_request_vars={
                    "ds_name": ds_name,
                    "painter_type": painter_type,
                },
            ),
            CascadingDropdown(
                title=_("Link"),
                choices=_column_link_choices(),
                orientation="horizontal",
            ),
            DropdownChoice(
                title=_("Tooltip"),
                choices=list(empty_choices) + list(painter_choices(_painters)),
            ),
        ]
        if painter_type == "join_painter":
            elements.extend(
                [
                    TextInput(
                        title=_("of Service"),
                        allow_empty=False,
                    ),
                    TextInput(title=_("Title")),
                ]
            )
        else:
            elements.extend([FixedValue(value=None, totext=""), FixedValue(value=None, totext="")])
        # UX/GUI Better ordering of fields and reason for transform
        elements.insert(1, elements.pop(3))
        return elements

    painters = painters_of_datasource(ds_name)
    vs_column: ValueSpec = Tuple(title=_("Column"), elements=column_elements(painters, "painter"))

    join_painters = join_painters_of_datasource(ds_name)
    if ident == "columns" and join_painters:
        vs_column = Alternative(
            elements=[
                vs_column,
                Tuple(
                    title=_("Joined column"),
                    help=_(
                        "A joined column can display information about specific services for "
                        "host objects in a view showing host objects. You need to specify the "
                        "service description of the service you like to show the data for."
                    ),
                    elements=column_elements(join_painters, "join_painter"),
                ),
            ],
            match=lambda x: 1 * (x is not None and x[1] is not None),
        )

    vs_column = Transform(
        valuespec=vs_column,
        back=lambda value: (value[0], value[2], value[3], value[1], value[4]),
        forth=lambda value: (value[0], value[3], value[1], value[2], value[4])
        if value is not None
        else None,
    )
    return (
        ident,
        Dictionary(
            title=title,
            render="form",
            optional_keys=False,
            elements=[
                (
                    ident,
                    ListOf(
                        valuespec=vs_column,
                        title=title,
                        add_label=_("Add column"),
                        allow_empty=allow_empty,
                        empty_text=empty_text,
                    ),
                ),
            ],
        ),
    )


def _column_link_choices() -> List[CascadingDropdownChoice]:
    return [
        (None, _("Do not add a link")),
        (
            "views",
            _("Link to view") + ":",
            DropdownChoice(
                choices=view_choices,
                sorted=True,
            ),
        ),
        (
            "dashboards",
            _("Link to dashboard") + ":",
            DropdownChoice(
                choices=visual_type_registry["dashboards"]().choices,
                sorted=True,
            ),
        ),
    ]


def view_editor_sorter_specs(view: ViewSpec) -> _Tuple[str, Dictionary]:
    def _sorter_choices(
        view: ViewSpec,
    ) -> Iterator[Union[DropdownChoiceEntry, CascadingDropdownChoice]]:
        ds_name = view["datasource"]

        for name, p in sorters_of_datasource(ds_name).items():
            # add all regular sortes. they may provide a third element: this
            # ValueSpec will be displayed after the sorter was choosen in the
            # CascadingDropdown.
            if isinstance(p, DerivedColumnsSorter) and (parameters := p.get_parameters()):
                yield name, get_plugin_title_for_choices(p), parameters
            else:
                yield name, get_plugin_title_for_choices(p)

        painter_spec: PainterSpec
        for painter_spec in view.get("painters", []):
            # look through all defined columns and add sorters for
            # svc_metrics_hist and svc_metrics_forecast columns.
            if isinstance(painter_spec[0], tuple) and (painter_name := painter_spec[0][0]) in [
                "svc_metrics_hist",
                "svc_metrics_forecast",
            ]:
                hist_sort = sorters_of_datasource(ds_name).get(painter_name)
                uuid = painter_spec[0][1].get("uuid", "")
                if hist_sort and uuid:
                    title = "History" if "hist" in painter_name else "Forecast"
                    yield (
                        "%s:%s" % (painter_name, uuid),
                        "Services: Metric %s - Column: %s"
                        % (title, painter_spec[0][1]["column_title"]),
                    )

    return (
        "sorting",
        Dictionary(
            title=_("Sorting"),
            render="form",
            optional_keys=False,
            elements=[
                (
                    "sorters",
                    ListOf(
                        valuespec=Tuple(
                            elements=[
                                CascadingDropdown(
                                    title=_("Column"),
                                    choices=list(_sorter_choices(view)),
                                    sorted=True,
                                    no_preselect_title="",
                                ),
                                DropdownChoice(
                                    title=_("Order"),
                                    choices=[(False, _("Ascending")), (True, _("Descending"))],
                                ),
                            ],
                            orientation="horizontal",
                        ),
                        title=_("Sorting"),
                        add_label=_("Add sorter"),
                    ),
                ),
            ],
        ),
    )


@page_registry.register_page("ajax_cascading_render_painer_parameters")
class PageAjaxCascadingRenderPainterParameters(AjaxPage):
    def page(self):
        api_request = request.get_request()

        if api_request["painter_type"] == "painter":
            painters = painters_of_datasource(api_request["ds_name"])
        elif api_request["painter_type"] == "join_painter":
            painters = join_painters_of_datasource(api_request["ds_name"])
        else:
            raise NotImplementedError()

        vs = CascadingDropdown(choices=painter_choices_with_params(painters))
        sub_vs = self._get_sub_vs(vs, ast.literal_eval(api_request["choice_id"]))
        value = ast.literal_eval(api_request["encoded_value"])

        with output_funnel.plugged():
            vs.show_sub_valuespec(api_request["varprefix"], sub_vs, value)
            return {"html_code": output_funnel.drain()}

    def _get_sub_vs(self, vs: CascadingDropdown, choice_id: object) -> ValueSpec:
        for val, _title, sub_vs in vs.choices():
            if val == choice_id:
                if sub_vs is None:
                    raise MKGeneralException("Choice does not have a ValueSpec")
                return sub_vs
        raise MKGeneralException("Invaild choice")


def render_view_config(view_spec: ViewSpec, general_properties=True):
    ds_name = view_spec.get("datasource", request.var("datasource"))
    if not ds_name:
        raise MKInternalError(_("No datasource defined."))
    if ds_name not in data_source_registry:
        raise MKInternalError(_("The given datasource is not supported."))

    view_spec["datasource"] = ds_name

    if general_properties:
        view_editor_general_properties(ds_name).render_input("view", view_spec.get("view"))

    for ident, vs in [
        view_editor_column_spec("columns", _("Columns"), ds_name),
        view_editor_sorter_specs(view_spec),
        view_editor_column_spec("grouping", _("Grouping"), ds_name),
    ]:
        vs.render_input(ident, view_spec.get(ident))


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

    if not view.get("topic"):
        view["topic"] = "other"

    view["view"]["options"] = []
    for key, _title in view_editor_options():
        if view.get(key):
            view["view"]["options"].append(key)

    view["visibility"] = {}
    for key in ["hidden", "hidebutton", "public"]:
        if view.get(key):
            view["visibility"][key] = view[key]

    view["grouping"] = {"grouping": view.get("group_painters", [])}
    view["sorting"] = {"sorters": view.get("sorters", {})}
    view["columns"] = {"columns": view.get("painters", [])}


def transform_valuespec_value_to_view(ident, attrs):
    # Transform some valuespec specific options to legacy view format.
    # We do not want to change the view data structure at the moment.

    if ident == "view":
        options = attrs.pop("options", [])
        if options:
            for option, _title in view_editor_options():
                attrs[option] = option in options

        return attrs

    if ident == "sorting":
        return attrs

    if ident == "grouping":
        return {"group_painters": attrs["grouping"]}

    if ident == "columns":
        return {"painters": [PainterSpec(*v) for v in attrs["columns"]]}

    return {ident: attrs}


# Extract properties of view from HTML variables and construct
# view object, to be used for saving or displaying
#
# old_view is the old view dict which might be loaded from storage.
# view is the new dict object to be updated.
def create_view_from_valuespec(old_view, view):
    ds_name = old_view.get("datasource", request.var("datasource"))
    view["datasource"] = ds_name

    def update_view(ident, vs):
        attrs = vs.from_html_vars(ident)
        vs.validate_value(attrs, ident)
        view.update(transform_valuespec_value_to_view(ident, attrs))

    for ident, vs in [
        ("view", view_editor_general_properties(ds_name)),
        view_editor_column_spec("columns", _("Columns"), ds_name),
        view_editor_column_spec("grouping", _("Grouping"), ds_name),
    ]:
        update_view(ident, vs)

    update_view(*view_editor_sorter_specs(view))
    return view


# .
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
    visuals.show_filter_form(
        info_list=view.datasource.infos,
        context={f.ident: view.context.get(f.ident, {}) for f in show_filters if f.available()},
        page_name=view.name,
        reset_ajax_page="ajax_initial_view_filters",
    )


class ABCAjaxInitialFilters(AjaxPage):
    @abc.abstractmethod
    def _get_context(self, page_name: str) -> VisualContext:
        raise NotImplementedError()

    def page(self) -> Dict[str, str]:
        api_request = self.webapi_request()
        varprefix = api_request.get("varprefix", "")
        page_name = api_request.get("page_name", "")
        context = self._get_context(page_name)
        page_request_vars = api_request.get("page_request_vars")
        assert isinstance(page_request_vars, dict)
        vs_filters = visuals.VisualFilterListWithAddPopup(info_list=page_request_vars["infos"])
        with output_funnel.plugged():
            vs_filters.render_input(varprefix, context)
            return {"filters_html": output_funnel.drain()}


@page_registry.register_page("ajax_initial_view_filters")
class AjaxInitialViewFilters(ABCAjaxInitialFilters):
    def _get_context(self, page_name: str) -> VisualContext:
        # Obtain the visual filters and the view context
        view_name = page_name
        try:
            view_spec = get_permitted_views()[view_name]
        except KeyError:
            raise MKUserError("view_name", _("The requested item %s does not exist") % view_name)

        datasource = data_source_registry[view_spec["datasource"]]()
        show_filters = visuals.filters_of_visual(
            view_spec, datasource.infos, link_filters=datasource.link_filters
        )
        view_context = view_spec.get("context", {})

        # Return a visual filters dict filled with the view context values
        return {f.ident: view_context.get(f.ident, {}) for f in show_filters if f.available()}


@cmk.gui.pages.register("view")
def page_view():
    """Central entry point for the initial HTML page rendering of a view"""
    with CPUTracker() as page_view_tracker:
        view_name = html.request.get_ascii_input_mandatory("view_name", "")
        view_spec = visuals.get_permissioned_visual(
            view_name,
            html.request.get_str_input("owner"),
            "view",
            get_permitted_views(),
            get_all_views(),
        )
        _patch_view_context(view_spec)

        datasource = data_source_registry[view_spec["datasource"]]()
        context = visuals.active_context_from_request(datasource.infos, view_spec["context"])

        view = View(view_name, view_spec, context)
        view.row_limit = get_limit()

        view.only_sites = visuals.get_only_sites_from_context(context)

        view.user_sorters = get_user_sorters()
        view.want_checkboxes = get_want_checkboxes()

        # Gather the page context which is needed for the "add to visual" popup menu
        # to add e.g. views to dashboards or reports
        visuals.set_page_context(context)

        # Need to be loaded before processing the painter_options below.
        # TODO: Make this dependency explicit
        display_options.load_from_html(request, html)

        painter_options = PainterOptions.get_instance()
        painter_options.load(view.name)
        painter_options.update_from_url(view)
        process_view(GUIViewRenderer(view, show_buttons=True))

    _may_create_slow_view_log_entry(page_view_tracker, view)


def _may_create_slow_view_log_entry(page_view_tracker: CPUTracker, view: View) -> None:
    duration_threshold = active_config.slow_views_duration_threshold
    if page_view_tracker.duration.process.elapsed < duration_threshold:
        return

    logger = log.logger.getChild("slow-views")
    logger.debug(
        (
            "View name: %s, User: %s, Row limit: %s, Limit type: %s, URL variables: %s"
            ", View context: %s, Unfiltered rows: %s, Filtered rows: %s, Rows after limit: %s"
            ", Duration fetching rows: %s, Duration filtering rows: %s, Duration rendering view: %s"
            ", Rendering page exceeds %ss: %s"
        ),
        view.name,
        user.id,
        view.row_limit,
        # as in get_limit()
        request.var("limit", "soft"),
        ["%s=%s" % (k, v) for k, v in request.itervars() if k != "selection" and v != ""],
        view.context,
        view.process_tracking.amount_unfiltered_rows,
        view.process_tracking.amount_filtered_rows,
        view.process_tracking.amount_rows_after_limit,
        _format_snapshot_duration(view.process_tracking.duration_fetch_rows),
        _format_snapshot_duration(view.process_tracking.duration_filter_rows),
        _format_snapshot_duration(view.process_tracking.duration_view_render),
        duration_threshold,
        _format_snapshot_duration(page_view_tracker.duration),
    )


def _format_snapshot_duration(snapshot: Snapshot) -> str:
    return "%.2fs" % snapshot.process.elapsed


def _patch_view_context(view_spec: ViewSpec) -> None:
    """Apply some hacks that are needed because for some edge cases in the view / visuals / context
    imlementation"""
    # FIXME TODO HACK to make grouping single contextes possible on host/service infos
    # Is hopefully cleaned up soon.
    # This is also somehow connected to the datasource.link_filters hack hat has been created for
    # linking hosts / services with groups
    if view_spec["datasource"] in ["hosts", "services"]:
        if request.has_var("hostgroup") and not request.has_var("opthost_group"):
            request.set_var("opthost_group", request.get_str_input_mandatory("hostgroup"))
        if request.has_var("servicegroup") and not request.has_var("optservice_group"):
            request.set_var("optservice_group", request.get_str_input_mandatory("servicegroup"))

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
        if not request.has_var("event_host") and request.has_var("host"):
            request.set_var("event_host", request.get_str_input_mandatory("host"))


def process_view(view_renderer: ABCViewRenderer) -> None:
    """Rendering all kind of views"""
    if request.var("mode") == "availability":
        _process_availability_view(view_renderer)
    else:
        _process_regular_view(view_renderer)


def _process_regular_view(view_renderer: ABCViewRenderer) -> None:
    all_active_filters = _get_all_active_filters(view_renderer.view)
    with livestatus.intercept_queries() as queries:
        unfiltered_amount_of_rows, rows = _get_view_rows(
            view_renderer.view,
            all_active_filters,
            only_count=False,
        )

    if html.output_format != "html":
        _export_view(view_renderer.view, rows)
        return

    _add_rest_api_menu_entries(view_renderer, queries)
    _show_view(view_renderer, unfiltered_amount_of_rows, rows)


def _add_rest_api_menu_entries(view_renderer, queries: List[str]):
    from cmk.utils.livestatus_helpers.queries import Query

    from cmk.gui.plugins.openapi.utils import create_url

    entries: List[PageMenuEntry] = []
    for text_query in set(queries):
        if "\nStats:" in text_query:
            continue
        try:
            query = Query.from_string(text_query)
        except ValueError:
            continue
        try:
            url = create_url(omd_site(), query)
        except ValueError:
            continue
        table = cast(str, query.table.__tablename__)
        entries.append(
            PageMenuEntry(
                title=_("Query %s resource") % (table,),
                icon_name="filter",
                item=make_external_link(url),
            )
        )
    view_renderer.append_menu_topic(
        dropdown="export",
        topic=PageMenuTopic(
            title="REST API",
            entries=entries,
        ),
    )


def _process_availability_view(view_renderer: ABCViewRenderer) -> None:
    view = view_renderer.view
    all_active_filters = _get_all_active_filters(view)

    # Fork to availability view. We just need the filter headers, since we do not query the normal
    # hosts and service table, but "statehist". This is *not* true for BI availability, though (see
    # later)
    if "aggr" not in view.datasource.infos or request.var("timeline_aggr"):
        filterheaders = "".join(get_livestatus_filter_headers(view.context, all_active_filters))
        # all 'amount_*', 'duration_fetch_rows' and 'duration_filter_rows' will be set in:
        show_view_func = lambda: availability.show_availability_page(view, filterheaders)
    else:
        _unfiltered_amount_of_rows, rows = _get_view_rows(
            view, all_active_filters, only_count=False
        )
        # 'amount_rows_after_limit' will be set in:
        show_view_func = lambda: availability.show_bi_availability(view, rows)

    with CPUTracker() as view_render_tracker:
        show_view_func()
    view.process_tracking.duration_view_render = view_render_tracker.duration


# TODO: Use livestatus Stats: instead of fetching rows?
def get_row_count(view: View) -> int:
    """Returns the number of rows shown by a view"""

    all_active_filters = _get_all_active_filters(view)
    # Check that all needed information for configured single contexts are available
    if view.missing_single_infos:
        raise MKUserError(
            None,
            _(
                "Missing context information: %s. You can either add this as a fixed "
                "setting, or call the with the missing HTTP variables."
            )
            % (", ".join(view.missing_single_infos)),
        )

    _unfiltered_amount_of_rows, rows = _get_view_rows(view, all_active_filters, only_count=True)
    return len(rows)


def _get_view_rows(
    view: View, all_active_filters: List[Filter], only_count: bool = False
) -> _Tuple[int, Rows]:
    with CPUTracker() as fetch_rows_tracker:
        rows, unfiltered_amount_of_rows = _fetch_view_rows(view, all_active_filters, only_count)

    # Sorting - use view sorters and URL supplied sorters
    _sort_data(view, rows, view.sorters)

    with CPUTracker() as filter_rows_tracker:
        # Apply non-Livestatus filters
        for filter_ in all_active_filters:
            rows = filter_.filter_table(view.context, rows)

    view.process_tracking.amount_unfiltered_rows = unfiltered_amount_of_rows
    view.process_tracking.amount_filtered_rows = len(rows)
    view.process_tracking.duration_fetch_rows = fetch_rows_tracker.duration
    view.process_tracking.duration_filter_rows = filter_rows_tracker.duration

    return unfiltered_amount_of_rows, rows


def _fetch_view_rows(
    view: View, all_active_filters: List[Filter], only_count: bool
) -> _Tuple[Rows, int]:
    """Fetches the view rows from livestatus

    Besides gathering the information from livestatus it also joins the rows with other information.
    For the moment this is:

    - Livestatus table joining (e.g. Adding service row info to host rows (For join painters))
    - Add HW/SW inventory data when needed
    - Add SLA data when needed
    """
    filterheaders = "".join(get_livestatus_filter_headers(view.context, all_active_filters))
    headers = filterheaders + view.spec.get("add_headers", "")

    # Fetch data. Some views show data only after pressing [Search]
    if (
        only_count
        or (not view.spec.get("mustsearch"))
        or request.var("filled_in") in ["filter", "actions", "confirm", "painteroptions"]
    ):
        columns = _get_needed_regular_columns(
            all_active_filters,
            view,
        )
        # We test for limit here and not inside view.row_limit, because view.row_limit is used
        # for rendering limits.
        query_row_limit = None if view.datasource.ignore_limit else view.row_limit
        row_data: Union[Rows, _Tuple[Rows, int]] = view.datasource.table.query(
            view, columns, headers, view.only_sites, query_row_limit, all_active_filters
        )

        if isinstance(row_data, tuple):
            rows, unfiltered_amount_of_rows = row_data
        else:
            rows = row_data
            unfiltered_amount_of_rows = len(row_data)

        # Now add join information, if there are join columns
        if view.join_cells:
            _do_table_join(view, rows, filterheaders, view.sorters)

        # If any painter, sorter or filter needs the information about the host's
        # inventory, then we load it and attach it as column "host_inventory"
        if _is_inventory_data_needed(view, all_active_filters):
            _add_inventory_data(rows)

        if not cmk_version.is_raw_edition():
            _add_sla_data(view, rows)

        return rows, unfiltered_amount_of_rows
    return [], 0


def _show_view(view_renderer: ABCViewRenderer, unfiltered_amount_of_rows: int, rows: Rows) -> None:
    view = view_renderer.view

    # Load from hard painter options > view > hard coded default
    painter_options = PainterOptions.get_instance()
    num_columns = painter_options.get("num_columns", view.spec.get("num_columns", 1))
    browser_reload = painter_options.get("refresh", view.spec.get("browser_reload", None))

    force_checkboxes = view.spec.get("force_checkboxes", False)
    show_checkboxes = force_checkboxes or request.var("show_checkboxes", "0") == "1"

    show_filters = visuals.filters_of_visual(
        view.spec, view.datasource.infos, link_filters=view.datasource.link_filters
    )

    # Set browser reload
    if browser_reload and display_options.enabled(display_options.R):
        html.set_browser_reload(browser_reload)

    if active_config.enable_sounds and active_config.sounds:
        for row in rows:
            save_state_for_playing_alarm_sounds(row)

    # Until now no single byte of HTML code has been output.
    # Now let's render the view
    with CPUTracker() as view_render_tracker:
        view_renderer.render(
            rows, show_checkboxes, num_columns, show_filters, unfiltered_amount_of_rows
        )
    view.process_tracking.duration_view_render = view_render_tracker.duration


def _get_all_active_filters(view: View) -> "List[Filter]":
    # Always allow the users to specify all allowed filters using the URL
    use_filters = list(visuals.filters_allowed_for_infos(view.datasource.infos).values())

    # See process_view() for more information about this hack
    if _is_ec_unrelated_host_view(view.spec):
        # Remove the original host name filter
        use_filters = [f for f in use_filters if f.ident != "host"]

    use_filters = [f for f in use_filters if f.available()]

    for filt in use_filters:
        # TODO: Clean this up! E.g. make the Filter class implement a default method
        if hasattr(filt, "derived_columns"):
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
        raise MKUserError(
            "output_format", _("Output format '%s' not supported") % html.output_format
        )

    exporter.handler(view, rows)


def _is_ec_unrelated_host_view(view_spec: ViewSpec) -> bool:
    # The "name" is not set in view report elements
    return (
        view_spec["datasource"] in ["mkeventd_events", "mkeventd_history"]
        and "host" in view_spec["single_infos"]
        and view_spec.get("name") != "ec_events_of_monhost"
    )


def _get_needed_regular_columns(
    all_active_filters: Iterable[Filter],
    view: View,
) -> List[ColumnName]:
    """Compute the list of all columns we need to query via Livestatus

    Those are: (1) columns used by the sorters in use, (2) columns use by column- and group-painters
    in use and - note - (3) columns used to satisfy external references (filters) of views we link
    to. The last bit is the trickiest. Also compute this list of view options use by the painters
    """
    # BI availability needs aggr_tree
    # TODO: wtf? a full reset of the list? Move this far away to a special place!
    if request.var("mode") == "availability" and "aggr" in view.datasource.infos:
        return ["aggr_tree", "aggr_name", "aggr_group"]

    columns = columns_of_cells(view.group_cells + view.row_cells)

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for entry in view.sorters:
        columns.update(entry.sorter.columns)

    # Add key columns, needed for executing commands
    columns.update(view.datasource.keys)

    # Add idkey columns, needed for identifying the row
    columns.update(view.datasource.id_keys)

    # Add columns requested by filters for post-livestatus filtering
    columns.update(
        chain.from_iterable(
            filter.columns_for_filter_table(view.context) for filter in all_active_filters
        )
    )

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
    if display_options.enabled(display_options.B) and "host" in view.datasource.infos:
        columns.add("host_labels")

    return list(columns)


def _get_needed_join_columns(
    join_cells: List[JoinCell], sorters: List[SorterEntry]
) -> List[ColumnName]:
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


def _is_inventory_data_needed(view: View, all_active_filters: "List[Filter]") -> bool:

    group_cells: List[Cell] = view.group_cells
    cells: List[Cell] = view.row_cells
    sorters: List[SorterEntry] = view.sorters

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
        if filt.need_inventory(view.context.get(filt.ident, {})):
            return True

    return False


def _add_inventory_data(rows: Rows) -> None:
    corrupted_inventory_files = []
    for row in rows:
        if "host_name" not in row:
            continue

        try:
            row["host_inventory"] = load_filtered_and_merged_tree(row)
        except LoadStructuredDataError:
            # The inventory row may be joined with other rows (perf-o-meter, ...).
            # Therefore we initialize the corrupt inventory tree with an empty tree
            # in order to display all other rows.
            row["host_inventory"] = StructuredDataNode()
            corrupted_inventory_files.append(str(get_short_inventory_filepath(row["host_name"])))

            if corrupted_inventory_files:
                user_errors.add(
                    MKUserError(
                        "load_structured_data_tree",
                        _(
                            "Cannot load HW/SW inventory trees %s. Please remove the corrupted files."
                        )
                        % ", ".join(sorted(corrupted_inventory_files)),
                    )
                )


def _add_sla_data(view: View, rows: Rows) -> None:
    import cmk.gui.cee.sla as sla  # pylint: disable=no-name-in-module,import-outside-toplevel

    sla_params = []
    for cell in view.row_cells:
        if cell.painter_name() in ["sla_specific", "sla_fixed"]:
            sla_params.append(cell.painter_parameters())
    if sla_params:
        sla_configurations_container = sla.SLAConfigurationsContainerFactory.create_from_cells(
            sla_params, rows
        )
        sla.SLAProcessor(sla_configurations_container).add_sla_data_to_rows(rows)


def columns_of_cells(cells: Sequence[Cell]) -> Set[ColumnName]:
    columns: Set[ColumnName] = set()
    for cell in cells:
        columns.update(cell.needed_columns())
    return columns


JoinMasterKey = _Tuple[SiteId, str]
JoinSlaveKey = str


def _do_table_join(
    view: View, master_rows: Rows, master_filters: str, sorters: List[SorterEntry]
) -> None:
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
    row_data = slave_ds.table.query(
        view,
        columns=list(set([join_master_column, join_slave_column] + join_columns)),
        headers=headers,
        only_sites=view.only_sites,
        limit=None,
        all_active_filters=[],
    )

    if isinstance(row_data, tuple):
        rows, _unfiltered_amount_of_rows = row_data
    else:
        rows = row_data

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


def save_state_for_playing_alarm_sounds(row: "Row") -> None:
    if not active_config.enable_sounds or not active_config.sounds:
        return

    # TODO: Move this to a generic place. What about -1?
    host_state_map = {0: "up", 1: "down", 2: "unreachable"}
    service_state_map = {0: "up", 1: "warning", 2: "critical", 3: "unknown"}

    for state_map, state in [
        (host_state_map, row.get("host_hard_state", row.get("host_state"))),
        (service_state_map, row.get("service_last_hard_state", row.get("service_state"))),
    ]:
        if state is None:
            continue

        try:
            state_name = state_map[int(state)]
        except KeyError:
            continue

        g.setdefault("alarm_sound_states", set()).add(state_name)


def play_alarm_sounds() -> None:
    if not active_config.enable_sounds or not active_config.sounds:
        return

    if "alarm_sound_states" not in g:
        return

    url = active_config.sound_url
    if not url.endswith("/"):
        url += "/"

    for state_name, wav in active_config.sounds:
        if not state_name or state_name in g.alarm_sound_states:
            html.play_sound(url + wav)
            break  # only one sound at one time


def get_user_sorters() -> List[SorterSpec]:
    """Returns a list of optionally set sort parameters from HTTP request"""
    return _parse_url_sorters(request.var("sort"))


def get_want_checkboxes() -> bool:
    """Whether or not the user requested checkboxes to be shown"""
    return request.get_integer_input_mandatory("show_checkboxes", 0) == 1


def get_limit() -> Optional[int]:
    """How many data rows may the user query?"""
    limitvar = request.var("limit", "soft")
    if limitvar == "hard" and user.may("general.ignore_soft_limit"):
        return active_config.hard_query_limit
    if limitvar == "none" and user.may("general.ignore_hard_limit"):
        return None
    return active_config.soft_query_limit


def _link_to_folder_by_path(path: str) -> str:
    """Return an URL to a certain WATO folder when we just know its path"""
    return makeuri_contextless(
        request,
        [("mode", "folder"), ("folder", path)],
        filename="wato.py",
    )


def _link_to_host_by_name(host_name: str) -> str:
    """Return an URL to the edit-properties of a host when we just know its name"""
    return makeuri_contextless(
        request,
        [("mode", "edit_host"), ("host", host_name)],
        filename="wato.py",
    )


def _get_context_page_menu_dropdowns(
    view: View, rows: Rows, mobile: bool
) -> List[PageMenuDropdown]:
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
    singlecontext_request_vars = visuals.get_singlecontext_vars(
        view.context, view.spec["single_infos"]
    )
    # Reports are displayed by separate dropdown (Export > Report)
    linked_visuals = list(
        _collect_linked_visuals(
            view, rows, singlecontext_request_vars, mobile, visual_types=["views", "dashboards"]
        )
    )

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
                topics=host_setup_topic
                + list(
                    _get_context_page_menu_topics(
                        view,
                        info,
                        is_single_info,
                        topics,
                        dropdown_visuals,
                        singlecontext_request_vars,
                        mobile,
                    )
                ),
            )
        )

    return dropdowns


def _get_ntop_page_menu_dropdown(view, host_address):
    return PageMenuDropdown(
        name="ntop",
        title="ntop",
        topics=_get_ntop_page_menu_topics(view, host_address),
    )


def _get_ntop_page_menu_topics(view, host_address):
    if "host" not in view.spec["single_infos"] or "host" in view.missing_single_infos:
        return []

    host_name = request.get_ascii_input_mandatory("host")
    # TODO insert icons when available
    topics = [
        PageMenuTopic(
            title="Network statistics",
            entries=[
                PageMenuEntry(
                    name="overview",
                    title="Host",
                    icon_name="folder",
                    item=_get_ntop_entry_item_link(host_name, host_address, "host_tab"),
                ),
                PageMenuEntry(
                    name="overview",
                    title="Traffic",
                    icon_name="trans",
                    item=_get_ntop_entry_item_link(host_name, host_address, "traffic_tab"),
                ),
                PageMenuEntry(
                    name="overview",
                    title="Packets",
                    icon_name="trans",
                    item=_get_ntop_entry_item_link(host_name, host_address, "packets_tab"),
                ),
                PageMenuEntry(
                    name="overview",
                    title="Ports",
                    icon_name="trans",
                    item=_get_ntop_entry_item_link(host_name, host_address, "ports_tab"),
                ),
                PageMenuEntry(
                    name="overview",
                    title="Peers",
                    icon_name="trans",
                    item=_get_ntop_entry_item_link(host_name, host_address, "peers_tab"),
                ),
                PageMenuEntry(
                    name="overview",
                    title="Apps",
                    icon_name="trans",
                    item=_get_ntop_entry_item_link(host_name, host_address, "applications_tab"),
                ),
                PageMenuEntry(
                    name="overview",
                    title="Flows",
                    icon_name="trans",
                    item=_get_ntop_entry_item_link(host_name, host_address, "flows_tab"),
                ),
            ],
        ),
        PageMenuTopic(
            title="Alerts",
            entries=[
                PageMenuEntry(
                    name="overview",
                    title="Engaged alerts",
                    icon_name="trans",
                    item=_get_ntop_entry_item_link(host_name, host_address, "engaged_alerts_tab"),
                ),
                PageMenuEntry(
                    name="overview",
                    title="Past alerts",
                    icon_name="trans",
                    item=_get_ntop_entry_item_link(host_name, host_address, "past_alerts_tab"),
                ),
                PageMenuEntry(
                    name="overview",
                    title="Flow alerts",
                    icon_name="trans",
                    item=_get_ntop_entry_item_link(host_name, host_address, "flow_alerts_tab"),
                ),
            ],
        ),
    ]

    return topics


def _get_ntop_entry_item_link(host_name: str, host_address: str, tab: str):
    return make_simple_link(
        makeuri(
            request,
            [
                ("host", host_name),
                ("host_address", host_address),
                ("tab", tab),
            ],
            filename="ntop_host_details.py",
            delvars=["view_name"],
        )
    )


def _get_context_page_menu_topics(
    view: View,
    info: VisualInfo,
    is_single_info: bool,
    topics: Dict[str, pagetypes.PagetypeTopics],
    dropdown_visuals: Iterator[_Tuple[VisualType, Visual]],
    singlecontext_request_vars: Dict[str, str],
    mobile: bool,
) -> Iterator[PageMenuTopic]:
    """Create the page menu topics for the given dropdown from the flat linked visuals list"""
    by_topic: Dict[pagetypes.PagetypeTopics, List[PageMenuEntry]] = {}

    for visual_type, visual in sorted(
        dropdown_visuals, key=lambda i: (i[1]["sort_index"], i[1]["title"])
    ):

        if visual.get("topic") == "bi" and not is_part_of_aggregation(
            singlecontext_request_vars.get("host"), singlecontext_request_vars.get("service")
        ):
            continue

        try:
            topic = topics[visual["topic"]]
        except KeyError:
            topic = topics["other"]

        entry = _make_page_menu_entry_for_visual(
            visual_type, visual, singlecontext_request_vars, mobile
        )

        by_topic.setdefault(topic, []).append(entry)

    if user.may("pagetype_topic.history"):
        if availability_entry := _get_availability_entry(view, info, is_single_info):
            by_topic.setdefault(topics["history"], []).append(availability_entry)

        if combined_graphs_entry := _get_combined_graphs_entry(view, info, is_single_info):
            by_topic.setdefault(topics["history"], []).append(combined_graphs_entry)

    # Return the sorted topics
    for topic, entries in sorted(by_topic.items(), key=lambda e: (e[0].sort_index(), e[0].title())):
        yield PageMenuTopic(
            title=topic.title(),
            entries=entries,
        )


def _get_visuals_for_page_menu_dropdown(
    linked_visuals: List[_Tuple[VisualType, Visual]], info: VisualInfo, is_single_info: bool
) -> Iterator[_Tuple[VisualType, Visual]]:
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


def collect_context_links(
    view: View, rows: Rows, mobile: bool, visual_types: SingleInfos
) -> Iterator[PageMenuEntry]:
    """Collect all visuals that share a context with visual. For example
    if a visual has a host context, get all relevant visuals."""
    # compute collections of set single context related request variables needed for this visual
    singlecontext_request_vars = visuals.get_singlecontext_vars(
        view.context, view.spec["single_infos"]
    )

    for visual_type, visual in _collect_linked_visuals(
        view, rows, singlecontext_request_vars, mobile, visual_types
    ):
        yield _make_page_menu_entry_for_visual(
            visual_type, visual, singlecontext_request_vars, mobile
        )


def _collect_linked_visuals(
    view: View,
    rows: Rows,
    singlecontext_request_vars: Dict[str, str],
    mobile: bool,
    visual_types: SingleInfos,
) -> Iterator[_Tuple[VisualType, Visual]]:
    for type_name in visual_type_registry.keys():
        if type_name in visual_types:
            yield from _collect_linked_visuals_of_type(
                type_name, view, rows, singlecontext_request_vars, mobile
            )


def _collect_linked_visuals_of_type(
    type_name: str, view: View, rows: Rows, singlecontext_request_vars: Dict[str, str], mobile: bool
) -> Iterator[_Tuple[VisualType, Visual]]:
    visual_type = visual_type_registry[type_name]()
    visual_type.load_handler()
    available_visuals = visual_type.permitted_visuals

    for visual in sorted(available_visuals.values(), key=lambda x: x.get("name") or ""):
        if visual == view.spec:
            continue

        if visual.get("hidebutton", False):
            continue  # this visual does not want a button to be displayed

        if not mobile and visual.get("mobile") or mobile and not visual.get("mobile"):
            continue

        # For dashboards and views we currently only show a link button,
        # if the target dashboard/view shares a single info with the
        # current visual.
        if not visual["single_infos"] and not visual_type.multicontext_links:
            continue  # skip non single visuals for dashboard, views

        # We can show a button only if all single contexts of the
        # target visual are known currently
        has_single_contexts = all(
            var in singlecontext_request_vars
            for var in visuals.get_single_info_keys(visual["single_infos"])
        )
        if not has_single_contexts:
            continue

        # Optional feature of visuals: Make them dynamically available as links or not.
        # This has been implemented for HW/SW inventory views which are often useless when a host
        # has no such information available. For example the "Oracle Tablespaces" inventory view
        # is useless on hosts that don't host Oracle databases.
        vars_values = get_linked_visual_request_vars(visual, singlecontext_request_vars)
        if not visual_type.link_from(view, rows, visual, vars_values):
            continue

        yield visual_type, visual


def _make_page_menu_entry_for_visual(
    visual_type: VisualType,
    visual: Visual,
    singlecontext_request_vars: Dict[str, str],
    mobile: bool,
) -> PageMenuEntry:
    return PageMenuEntry(
        title=visual["title"],
        icon_name=visual.get("icon") or "trans",
        item=make_simple_link(
            make_linked_visual_url(visual_type, visual, singlecontext_request_vars, mobile)
        ),
        name="cb_" + visual["name"],
        is_show_more=visual.get("is_show_more", False),
    )


def _get_availability_entry(
    view: View, info: VisualInfo, is_single_info: bool
) -> Optional[PageMenuEntry]:
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
        item=make_simple_link(
            makeuri(request, [("mode", "availability")], delvars=["show_checkboxes", "selection"])
        ),
        is_enabled=not view.missing_single_infos,
        disabled_tooltip=_("Missing required context information")
        if view.missing_single_infos
        else None,
    )


def _show_current_view_availability_context_button(view: View) -> bool:
    if not user.may("general.see_availability"):
        return False

    if "aggr" in view.datasource.infos:
        return True

    return view.datasource.ident in ["hosts", "services"]


def _get_combined_graphs_entry(
    view: View, info: VisualInfo, is_single_info: bool
) -> Optional[PageMenuEntry]:
    """Detect whether or not to add a combined graphs link to the dropdown currently being rendered

    In which dropdown to expect the "All metrics of same type in one graph" link?

    """
    if not _show_combined_graphs_context_button(view):
        return None

    if not _show_in_current_dropdown(view, info.ident, is_single_info):
        return None

    httpvars: HTTPVariables = [
        ("single_infos", ",".join(view.spec["single_infos"])),
        ("datasource", view.datasource.ident),
        ("view_title", view_title(view.spec, view.context)),
    ]

    url = makeuri(
        request, httpvars, filename="combined_graphs.py", delvars=["show_checkboxes", "selection"]
    )
    return PageMenuEntry(
        title=_("All metrics of same type in one graph"),
        icon_name="graph",
        item=make_simple_link(url),
    )


def _show_combined_graphs_context_button(view: View) -> bool:
    if cmk_version.is_raw_edition():
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
    raise ValueError(
        "Can not decide whether or not to show this button: %s, %s" % (info_name, datasource.ident)
    )


def _page_menu_host_setup_topic(view: View) -> List[PageMenuTopic]:
    if "host" not in view.spec["single_infos"] or "host" in view.missing_single_infos:
        return []

    if not active_config.wato_enabled:
        return []

    if not user.may("wato.use"):
        return []

    if not user.may("wato.hosts") and not user.may("wato.seeall"):
        return []

    host_name = view.context["host"]["host"]

    return [
        PageMenuTopic(
            title=_("Setup"),
            entries=list(page_menu_entries_host_setup(host_name)),
        )
    ]


def page_menu_entries_host_setup(host_name: str) -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Host configuration"),
        icon_name={
            "icon": "folder",
            "emblem": "settings",
        },
        item=make_simple_link(_link_to_host_by_name(host_name)),
    )

    yield PageMenuEntry(
        title=_("Service configuration"),
        icon_name={
            "icon": "services",
            "emblem": "settings",
        },
        item=make_simple_link(
            makeuri_contextless(
                request,
                [("mode", "inventory"), ("host", host_name)],
                filename="wato.py",
            )
        ),
    )

    is_cluster = False
    if is_cluster:
        yield PageMenuEntry(
            title=_("Connection tests"),
            icon_name="diagnose",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "diag_host"), ("host", host_name)],
                    filename="wato.py",
                )
            ),
        )

    if user.may("wato.rulesets"):
        yield PageMenuEntry(
            title=_("Effective parameters"),
            icon_name="rulesets",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "object_parameters"), ("host", host_name)],
                    filename="wato.py",
                )
            ),
        )

        yield PageMenuEntry(
            title=_("Rules"),
            icon_name="rulesets",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [
                        ("mode", "rule_search"),
                        ("filled_in", "search"),
                        ("search_p_ruleset_deprecated", "OFF"),
                        ("search_p_rule_host_list_USE", "ON"),
                        ("search_p_rule_host_list", host_name),
                    ],
                    filename="wato.py",
                )
            ),
        )


def _sort_data(view: View, data: "Rows", sorters: List[SorterEntry]) -> None:
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
                c = neg * safe_compare(
                    entry.sorter.cmp, e1["JOIN"].get(entry.join_key), e2["JOIN"].get(entry.join_key)
                )
            else:
                c = neg * entry.sorter.cmp(e1, e2)

            if c != 0:
                return c
        return 0  # equal

    data.sort(key=functools.cmp_to_key(multisort))


def sorters_of_datasource(ds_name: str) -> Mapping[str, Sorter]:
    return _allowed_for_datasource(sorter_registry, ds_name)


def painters_of_datasource(ds_name: str) -> Mapping[str, Painter]:
    return _allowed_for_datasource(painter_registry, ds_name)


def join_painters_of_datasource(ds_name: str) -> Mapping[str, Painter]:
    datasource = data_source_registry[ds_name]()
    if datasource.join is None:
        return {}  # no joining with this datasource

    # Get the painters allowed for the join "source" and "target"
    painters = painters_of_datasource(ds_name)
    join_painters_unfiltered = _allowed_for_datasource(painter_registry, datasource.join[0])

    # Filter out painters associated with the "join source" datasource
    join_painters: Dict[str, Painter] = {}
    for key, val in join_painters_unfiltered.items():
        if key not in painters:
            join_painters[key] = val

    return join_painters


@overload
def _allowed_for_datasource(collection: PainterRegistry, ds_name: str) -> Mapping[str, Painter]:
    ...


@overload
def _allowed_for_datasource(collection: SorterRegistry, ds_name: str) -> Mapping[str, Sorter]:
    ...


# Filters a list of sorters or painters and decides which of
# those are available for a certain data source
def _allowed_for_datasource(
    collection: Union[PainterRegistry, SorterRegistry],
    ds_name: str,
) -> Mapping[str, Union[Sorter, Painter]]:
    datasource = data_source_registry[ds_name]()
    infos_available = set(datasource.infos)
    add_columns = datasource.add_columns

    allowed: Dict[str, Union[Sorter, Painter]] = {}
    for name, plugin_class in collection.items():
        plugin = plugin_class()
        infos_needed = infos_needed_by_plugin(plugin, add_columns)
        if len(infos_needed.difference(infos_available)) == 0:
            allowed[name] = plugin
    return allowed


def infos_needed_by_plugin(
    plugin: Union[Painter, Sorter], add_columns: Optional[List] = None
) -> Set[str]:
    if add_columns is None:
        add_columns = []

    return {c.split("_", 1)[0] for c in plugin.columns if c != "site" and c not in add_columns}


def painter_choices(painters: Dict[str, Painter]) -> DropdownChoiceEntries:
    return [(c[0], c[1]) for c in painter_choices_with_params(painters)]


def painter_choices_with_params(painters: Mapping[str, Painter]) -> List[CascadingDropdownChoice]:
    return sorted(
        (
            (
                name,
                get_plugin_title_for_choices(painter),
                painter.parameters if painter.parameters else None,
            )
            for name, painter in painters.items()
        ),
        key=lambda x: x[1],
    )


def get_plugin_title_for_choices(plugin: Union[Painter, Sorter]) -> str:
    info_title = "/".join(
        [
            visual_info_registry[info_name]().title_plural
            for info_name in sorted(infos_needed_by_plugin(plugin))
        ]
    )

    # TODO: Cleanup the special case for sites. How? Add an info for it?
    if plugin.columns == ["site"]:
        info_title = _("Site")

    dummy_cell = Cell(View("", {}, {}), PainterSpec(plugin.ident))
    title: str
    if isinstance(plugin, Painter):
        title = plugin.list_title(dummy_cell)
    else:
        if callable(plugin.title):
            title = plugin.title(dummy_cell)
        else:
            title = plugin.title

    return "%s: %s" % (info_title, title)


# .
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


def _should_show_command_form(
    datasource: ABCDataSource, ignore_display_option: bool = False
) -> bool:
    """Whether or not this view handles commands for the current user

    When it does not handle commands the command tab, command form, row
    selection and processing commands is disabled.
    """
    if not ignore_display_option and display_options.disabled(display_options.C):
        return False
    if not user.may("general.act"):
        return False

    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource.infos[0]
    for command_class in command_registry.values():
        command = command_class()
        if what in command.tables and user.may(command.permission.name):
            return True

    return False


def _get_command_groups(info_name: InfoName) -> Dict[Type[CommandGroup], List[Command]]:
    by_group: Dict[Type[CommandGroup], List[Command]] = {}

    for command_class in command_registry.values():
        command = command_class()
        if info_name in command.tables and user.may(command.permission.name):
            # Some special commands can be shown on special views using this option.  It is
            # currently only used by custom commands, not shipped with Checkmk.
            if command.only_view and request.var("view_name") != command.only_view:
                continue
            by_group.setdefault(command.group, []).append(command)

    return by_group


def core_command(
    what: str, row: Row, row_nr: int, total_rows: int
) -> _Tuple[Sequence[CommandSpec], List[_Tuple[str, str]], str, CommandExecutor]:
    """Examine the current HTML variables in order determine, which command the user has selected.
    The fetch ids from a data row (host name, service description, downtime/commands id) and
    construct one or several core command lines and a descriptive title."""
    host = row.get("host_name")
    descr = row.get("service_description")

    if what == "host":
        assert isinstance(host, str)
        spec: str = host
        cmdtag = "HOST"

    elif what == "service":
        assert isinstance(host, str)
        assert isinstance(descr, str)
        spec = "%s;%s" % (host, descr)
        cmdtag = "SVC"

    else:
        # e.g. downtime_id for downtimes may be int, same for acknowledgements
        spec = str(row[what + "_id"])
        if descr:
            cmdtag = "SVC"
        else:
            cmdtag = "HOST"
    assert isinstance(spec, str)

    commands, title = None, None
    # Call all command actions. The first one that detects
    # itself to be executed (by examining the HTML variables)
    # will return a command to execute and a title for the
    # confirmation dialog.
    for cmd_class in command_registry.values():
        cmd = cmd_class()
        if user.may(cmd.permission.name):
            result = cmd.action(cmdtag, spec, row, row_nr, total_rows)
            confirm_options = cmd.user_confirm_options(total_rows, cmdtag)
            if result:
                executor = cmd.executor
                commands, title = result
                break

    if commands is None or title is None:
        raise MKUserError(None, _("Sorry. This command is not implemented."))

    # Some commands return lists of commands, others
    # just return one basic command. Convert those
    if isinstance(commands, str):
        commands = [commands]

    return commands, confirm_options, title, executor


# Returns:
# True -> Actions have been done
# False -> No actions done because now rows selected
def do_actions(view: ViewSpec, what: InfoName, action_rows: Rows, backurl: str) -> bool:
    if not user.may("general.act"):
        html.show_error(
            _(
                "You are not allowed to perform actions. "
                "If you think this is an error, please ask "
                "your administrator grant you the permission to do so."
            )
        )
        return False  # no actions done

    if not action_rows:
        message_no_rows = _("No rows selected to perform actions for.")
        message_no_rows += '<br><a href="%s">%s</a>' % (backurl, _("Back to view"))
        html.show_error(message_no_rows)
        return False  # no actions done

    command = None
    confirm_options, cmd_title, executor = core_command(what, action_rows[0], 0, len(action_rows),)[
        1:4
    ]  # just get confirm_options, title and executor

    command_title = _("Do you really want to %s") % cmd_title
    if not confirm_with_preview(command_title, confirm_options, method="GET"):
        return False

    if request.has_var("_do_confirm_host_downtime"):
        request.set_var("_on_hosts", "on")

    count = 0
    already_executed = set()
    for nr, row in enumerate(action_rows):
        core_commands, _confirm_options, _title, executor = core_command(
            what,
            row,
            nr,
            len(action_rows),
        )
        for command_entry in core_commands:
            site: Optional[str] = row.get(
                "site"
            )  # site is missing for BI rows (aggregations can spawn several sites)
            if (site, command_entry) not in already_executed:
                # Some command functions return the information about the site per-command (e.g. for BI)
                if isinstance(command_entry, tuple):
                    site, command = command_entry
                else:
                    command = command_entry

                executor(command, SiteId(site) if site else None)
                already_executed.add((site, command_entry))
                count += 1

    message = None
    if command:
        message = _("Successfully sent %d commands.") % count
        if active_config.debug:
            message += _("The last one was: <pre>%s</pre>") % command
    elif count == 0:
        message = _("No matching data row. No command sent.")

    if message:
        backurl += "&filled_in=filter&_show_filter_form=0"
        message += '<br><a href="%s">%s</a>' % (backurl, _("Back to view"))
        if request.var("show_checkboxes") == "1":
            request.del_var("selection")
            weblib.selection_id()
            backurl += "&selection=" + request.get_str_input_mandatory("selection")
            message += '<br><a href="%s">%s</a>' % (
                backurl,
                _("Back to view with checkboxes reset"),
            )
        if request.var("_show_result") == "0":
            html.immediate_browser_redirect(0.5, backurl)
        html.show_message(message)

    return True


def _filter_selected_rows(view_spec: ViewSpec, rows: Rows, selected_ids: List[str]) -> Rows:
    action_rows: Rows = []
    for row in rows:
        if row_id(view_spec, row) in selected_ids:
            action_rows.append(row)
    return action_rows


@cmk.gui.pages.register("export_views")
def ajax_export() -> None:
    for view in get_permitted_views().values():
        view["owner"] = ""
        view["public"] = True
    response.set_data(pprint.pformat(get_permitted_views()))


def get_view_by_name(view_name: ViewName) -> ViewSpec:
    return get_permitted_views()[view_name]


# .
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
def ajax_popup_icon_selector() -> None:
    varprefix = request.var("varprefix")
    value = request.var("value")
    allow_empty = request.var("allow_empty") == "1"
    show_builtin_icons = request.var("show_builtin_icons") == "1"

    vs = IconSelector(allow_empty=allow_empty, show_builtin_icons=show_builtin_icons)
    vs.render_popup_input(varprefix, value)


# .
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


def query_action_data(
    what: IconObjectType, host: HostName, site: SiteId, svcdesc: Optional[ServiceName]
) -> Row:
    # Now fetch the needed data from livestatus
    columns = list(iconpainter_columns(what, toplevel=False))
    try:
        columns.remove("site")
    except KeyError:
        pass

    query = livestatus_lql([host], columns, svcdesc)

    with sites.prepend_site(), sites.only_sites(site):
        row = sites.live().query_row(query)

    return dict(zip(["site"] + columns, row))


@cmk.gui.pages.register("ajax_popup_action_menu")
def ajax_popup_action_menu() -> None:
    site = SiteId(request.get_ascii_input_mandatory("site"))
    host = HostName(request.get_ascii_input_mandatory("host"))
    svcdesc = request.get_str_input("service")
    what: IconObjectType = "service" if svcdesc else "host"

    display_options.load_from_html(request, html)

    row = query_action_data(what, host, site, svcdesc)
    icons = get_icons(what, row, toplevel=False)

    html.open_ul()
    for icon in icons:
        if isinstance(icon, LegacyIconEntry):
            html.open_li()
            html.write_text(icon.code)
            html.close_li()
        elif isinstance(icon, IconEntry):
            html.open_li()
            if icon.url_spec:
                url, target_frame = transform_action_url(icon.url_spec)
                url = replace_action_url_macros(url, what, row)
                onclick = None
                if url.startswith("onclick:"):
                    onclick = url[8:]
                    url = "javascript:void(0);"
                html.open_a(href=url, target=target_frame, onclick=onclick)

            html.icon(icon.icon_name)
            if icon.title:
                html.write_text(icon.title)
            else:
                html.write_text(_("No title"))
            if icon.url_spec:
                html.close_a()
            html.close_li()
    html.close_ul()


# .
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

    def page(self) -> AjaxPageResult:
        api_request = request.get_request()
        return self._do_reschedule(api_request)

    @staticmethod
    def _force_check(now: int, cmd: str, spec: str, site: SiteId) -> None:
        sites.live().command(
            "[%d] SCHEDULE_FORCED_%s_CHECK;%s;%d" % (now, cmd, livestatus.lqencode(spec), now), site
        )

    @staticmethod
    def _wait_for(
        site: SiteId, host: str, what: str, wait_spec: str, now: int, add_filter: str
    ) -> livestatus.LivestatusRow:
        with sites.only_sites(site):
            return sites.live().query_row(
                (
                    "GET %ss\n"
                    "WaitObject: %s\n"
                    "WaitCondition: last_check >= %d\n"
                    "WaitTimeout: %d\n"
                    "WaitTrigger: check\n"
                    "Columns: last_check state plugin_output\n"
                    "Filter: host_name = %s\n%s"
                )
                % (
                    what,
                    livestatus.lqencode(wait_spec),
                    now,
                    active_config.reschedule_timeout * 1000,
                    livestatus.lqencode(host),
                    add_filter,
                )
            )

    def _do_reschedule(self, api_request: Dict[str, Any]) -> AjaxPageResult:
        if not user.may("action.reschedule"):
            raise MKGeneralException("You are not allowed to reschedule checks.")

        site = api_request.get("site")
        host = api_request.get("host")
        if not host or not site:
            raise MKGeneralException("Action reschedule: missing host name")

        service = api_request.get("service", "")
        wait_svc = api_request.get("wait_svc", "")

        if service:
            cmd = "SVC"
            what = "service"
            spec = "%s;%s" % (host, service)

            if wait_svc:
                wait_spec = "%s;%s" % (host, wait_svc)
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

        if service in ("Check_MK Discovery", "Check_MK Inventory"):
            # During discovery, the allowed cache age is (by default) 120 seconds, such that the
            # discovery service won't steal data in the TCP case.
            # But we do want to see new services, so for SNMP we set the cache age to zero.
            # For TCP, we ensure updated caches by triggering the "Check_MK" service whenever the
            # user manually triggers "Check_MK Discovery".
            self._force_check(now, "SVC", f"{host};Check_MK", site)
            _row = self._wait_for(
                site,
                host,
                "service",
                f"{host};Check_MK",
                now,
                "Filter: service_description = Check_MK\n",
            )

        self._force_check(now, cmd, spec, site)
        row = self._wait_for(site, host, what, wait_spec, now, add_filter)

        last_check = row[0]
        if last_check < now:
            return {
                "state": "TIMEOUT",
                "message": _("Check not executed within %d seconds")
                % (active_config.reschedule_timeout),
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
