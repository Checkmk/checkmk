#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import functools
import pprint
import time
from itertools import chain
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Set
from typing import Tuple as _Tuple
from typing import Union

import livestatus
from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.prediction import livestatus_lql
from cmk.utils.site import omd_site
from cmk.utils.structured_data import SDPath, StructuredDataNode
from cmk.utils.type_defs import HostName, ServiceName, UserId

import cmk.gui.log as log
import cmk.gui.pages
import cmk.gui.sites as sites
import cmk.gui.utils as utils
import cmk.gui.view_utils
import cmk.gui.views.datasource_selection as _datasource_selection
import cmk.gui.visuals as visuals
from cmk.gui.config import (
    active_config,
    default_authorized_builtin_role_ids,
    register_post_config_load_hook,
)
from cmk.gui.ctx_stack import g
from cmk.gui.data_source import data_source_registry
from cmk.gui.derived_columns_sorter import DerivedColumnsSorter
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKGeneralException, MKMissingDataError, MKUserError
from cmk.gui.exporter import exporter_registry
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _u
from cmk.gui.inventory import (
    get_short_inventory_filepath,
    get_status_data_via_livestatus,
    load_filtered_and_merged_tree,
    load_latest_delta_tree,
    LoadStructuredDataError,
)
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_external_link, PageMenuEntry, PageMenuTopic
from cmk.gui.pages import AjaxPage, page_registry, PageResult
from cmk.gui.painter_options import PainterOptions
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    declare_permission,
    permission_section_registry,
    PermissionSection,
)
from cmk.gui.plugins.views.icons.utils import (
    get_icons,
    Icon,
    icon_and_action_registry,
    IconEntry,
    IconObjectType,
    iconpainter_columns,
    LegacyIconEntry,
    multisite_icons_and_actions,
)
from cmk.gui.plugins.views.utils import (
    Cell,
    get_tag_groups,
    JoinCell,
    load_used_options,
    Painter,
    painter_registry,
    register_legacy_command,
    register_painter,
    replace_action_url_macros,
    transform_action_url,
)
from cmk.gui.plugins.visuals.utils import (
    Filter,
    get_livestatus_filter_headers,
    visual_type_registry,
    VisualType,
)
from cmk.gui.sorter import register_sorter, SorterEntry
from cmk.gui.type_defs import (
    ColumnName,
    HTTPVariables,
    Perfdata,
    PerfometerSpec,
    Row,
    Rows,
    SorterSpec,
    TranslatedMetrics,
    ViewSpec,
    VisualContext,
)
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import Hostname, IconSelector
from cmk.gui.view import View
from cmk.gui.view_renderer import ABCViewRenderer, GUIViewRenderer
from cmk.gui.view_store import get_all_views, get_permitted_views, multisite_builtin_views
from cmk.gui.view_utils import get_labels, render_labels, render_tag_groups
from cmk.gui.views.builtin_views import builtin_views
from cmk.gui.views.inventory import register_table_views_and_columns, update_paint_functions
from cmk.gui.views.page_edit_view import (
    format_view_title,
    page_edit_view,
    PageAjaxCascadingRenderPainterParameters,
)

from . import availability

# TODO: Kept for compatibility with pre 1.6 plugins. Plugins will not be used anymore, but an error
# will be displayed.
multisite_painter_options: Dict[str, Any] = {}
multisite_layouts: Dict[str, Any] = {}
multisite_commands: List[Dict[str, Any]] = []
multisite_datasources: Dict[str, Any] = {}
multisite_painters: Dict[str, Dict[str, Any]] = {}
multisite_sorters: Dict[str, Any] = {}


cmk.gui.pages.register("create_view")(_datasource_selection.page_create_view)
cmk.gui.pages.register("edit_view")(page_edit_view)
page_registry.register_page("ajax_cascading_render_painer_parameters")(
    PageAjaxCascadingRenderPainterParameters
)


@visual_type_registry.register
class VisualTypeViews(VisualType):
    """Register the views as a visual type"""

    @property
    def ident(self) -> str:
        return "views"

    @property
    def title(self) -> str:
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

    def link_from(  # type:ignore[no-untyped-def]
        self, linking_view, linking_view_rows, visual, context_vars: HTTPVariables
    ) -> bool:
        """This has been implemented for HW/SW inventory views which are often useless when a host
        has no such information available. For example the "Oracle Tablespaces" inventory view is
        useless on hosts that don't host Oracle databases."""
        result = super().link_from(linking_view, linking_view_rows, visual, context_vars)
        if result is False:
            return False

        link_from = visual["link_from"]
        if not link_from:
            return True  # No link from filtering: Always display this.

        context = dict(context_vars)
        if (hostname := context.get("host")) is None:
            # No host data? Keep old behaviour
            return True

        if hostname == "":
            return False

        # TODO: host is not correctly validated by visuals. Do it here for the moment.
        try:
            Hostname().validate_value(hostname, None)
        except MKUserError:
            return False

        if not (site_id := context.get("site")):
            return False

        return _has_inventory_tree(
            HostName(hostname),
            SiteId(str(site_id)),
            link_from.get("has_inventory_tree", []),
            is_history=False,
        ) or _has_inventory_tree(
            HostName(hostname),
            SiteId(str(site_id)),
            link_from.get("has_inventory_tree_history", []),
            is_history=True,
        )


def _has_inventory_tree(
    hostname: HostName,
    site_id: SiteId,
    paths: Sequence[SDPath],
    is_history: bool,
) -> bool:
    if not paths:
        return False

    # FIXME In order to decide whether this view is enabled
    # do we really need to load the whole tree?
    try:
        struct_tree = _get_struct_tree(is_history, hostname, site_id)
    except LoadStructuredDataError:
        return False

    if not struct_tree:
        return False

    if struct_tree.is_empty():
        return False

    return any(
        (node := struct_tree.get_node(path)) is not None and not node.is_empty() for path in paths
    )


def _get_struct_tree(
    is_history: bool, hostname: HostName, site_id: SiteId
) -> Optional[StructuredDataNode]:
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
    def name(self) -> str:
        return "view"

    @property
    def title(self) -> str:
        return _("Views")

    @property
    def do_sort(self):
        return True


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("views", globals())
    update_paint_functions(globals())

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
    register_table_views_and_columns()

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
            "%s - %s" % (name, _u(str(view_spec["description"]))),
            default_authorized_builtin_role_ids,
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
    import cmk.gui.data_source as data_source
    import cmk.gui.exporter as exporter
    import cmk.gui.livestatus_data_source as livestatus_data_source
    import cmk.gui.painter_options as painter_options
    import cmk.gui.plugins.views as api_module
    import cmk.gui.plugins.views.utils as plugin_utils
    import cmk.gui.sorter as sorter
    import cmk.gui.view_store as view_store
    import cmk.gui.visual_link as visual_link

    for name in (
        "ABCDataSource",
        "data_source_registry",
        "row_id",
        "RowTable",
    ):
        api_module.__dict__[name] = data_source.__dict__[name]

    for name in (
        "Exporter",
        "exporter_registry",
    ):
        api_module.__dict__[name] = exporter.__dict__[name]

    for name in (
        "DataSourceLivestatus",
        "RowTableLivestatus",
        "query_livestatus",
    ):
        api_module.__dict__[name] = livestatus_data_source.__dict__[name]

    for name in (
        "get_graph_timerange_from_painter_options",
        "paint_age",
        "painter_option_registry",
        "PainterOption",
        "PainterOptions",
    ):
        api_module.__dict__[name] = painter_options.__dict__[name]

    for name in (
        "declare_simple_sorter",
        "register_sorter",
        "Sorter",
        "sorter_registry",
    ):
        api_module.__dict__[name] = sorter.__dict__[name]
    api_module.__dict__["DerivedColumnsSorter"] = DerivedColumnsSorter

    for name in (
        "get_permitted_views",
        "multisite_builtin_views",
    ):
        api_module.__dict__[name] = view_store.__dict__[name]

    for name in (
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
        "declare_1to1_sorter",
        "display_options",
        "EmptyCell",
        "ExportCellContent",
        "format_plugin_output",
        "get_label_sources",
        "get_perfdata_nth_value",
        "get_tag_groups",
        "group_value",
        "inventory_displayhints",
        "InventoryHintSpec",
        "is_stale",
        "join_row",
        "Layout",
        "layout_registry",
        "output_csv_headers",
        "paint_host_list",
        "paint_nagiosflag",
        "paint_stalified",
        "Painter",
        "painter_registry",
        "register_painter",
        "render_cache_info",
        "replace_action_url_macros",
        "Row",
        "transform_action_url",
        "view_is_enabled",
        "view_title",
        "VisualLinkSpec",
    ):
        api_module.__dict__[name] = plugin_utils.__dict__[name]

    for name in (
        "render_link_to_view",
        "url_to_visual",
    ):
        api_module.__dict__[name] = visual_link.__dict__[name]

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
                "group_by": lambda self, row, _cell: _paint_host_tag(row, self._tag_group_id)[1],
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


def _get_tag_group_value(row, what, tag_group_id) -> str:  # type:ignore[no-untyped-def]
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
def page_edit_views() -> None:
    cols = [(_("Datasource"), lambda v: data_source_registry[v["datasource"]]().title)]
    # Intermediate step. Will be cleaned up once all visuals are TypedDicts
    visuals.page_list("views", _("Edit Views"), get_all_views(), cols)  # type: ignore[arg-type]


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


@cmk.gui.pages.register("create_view_infos")
def page_create_view_infos() -> None:
    ds_class, ds_name = request.get_item_input("datasource", data_source_registry)
    visuals.page_create_visual(
        "views",
        ds_class().infos,
        next_url="edit_view.py?mode=create&datasource=%s&single_infos=%%s" % ds_name,
    )


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
        view_name = request.get_ascii_input_mandatory("view_name", "")
        view_spec = visuals.get_permissioned_visual(
            view_name,
            request.get_validated_type_input(UserId, "owner"),
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
        painter_options.update_from_url(
            view.name, load_used_options(view.spec, view.group_cells + view.row_cells)
        )
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


def _add_rest_api_menu_entries(view_renderer, queries: List[str]):  # type:ignore[no-untyped-def]
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
        table = query.table.__tablename__
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
        show_view_func = functools.partial(
            availability.show_availability_page,
            view=view,
            filterheaders=filterheaders,
        )

    else:
        _unfiltered_amount_of_rows, rows = _get_view_rows(
            view, all_active_filters, only_count=False
        )
        # 'amount_rows_after_limit' will be set in:
        show_view_func = functools.partial(
            availability.show_bi_availability,
            view=view,
            aggr_rows=rows,
        )

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
            try:
                rows = filter_.filter_table(view.context, rows)
            except MKMissingDataError as e:
                view.add_warning_message(str(e))

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
            view.datasource,
            view.row_cells,
            columns,
            view.context,
            headers,
            view.only_sites,
            query_row_limit,
            all_active_filters,
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
        html.browser_reload = browser_reload

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
            filt.derived_columns(view.row_cells)  # type: ignore[attr-defined]

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
        view.datasource,
        view.row_cells,
        columns=list(set([join_master_column, join_slave_column] + join_columns)),
        context=view.context,
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


def _parse_url_sorters(sort: Optional[str]) -> list[SorterSpec]:
    sorters: list[SorterSpec] = []
    if not sort:
        return sorters
    for s in sort.split(","):
        if "~" in s:
            sorter, join_index = s.split("~", 1)
        else:
            sorter, join_index = s, None

        negate = False
        if sorter.startswith("-"):
            negate = True
            sorter = sorter[1:]

        sorters.append(SorterSpec(sorter, negate, join_index))
    return sorters


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


@cmk.gui.pages.register("export_views")
def ajax_export() -> None:
    for view in get_permitted_views().values():
        view["owner"] = ""
        view["public"] = True
    response.set_data(pprint.pformat(get_permitted_views()))


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
    assert varprefix is not None  # Hmmm...
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

    def page(self) -> PageResult:
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

    def _do_reschedule(self, api_request: Dict[str, Any]) -> PageResult:
        if not user.may("action.reschedule"):
            raise MKGeneralException("You are not allowed to reschedule checks.")

        check_csrf_token()

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
            self._wait_for(
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
