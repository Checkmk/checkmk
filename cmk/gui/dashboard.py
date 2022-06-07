#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKException

import cmk.gui.crash_handler as crash_handler
import cmk.gui.forms as forms
import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.utils as utils
import cmk.gui.visuals as visuals
from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_topic_breadcrumb,
)
from cmk.gui.config import builtin_role_ids
from cmk.gui.exceptions import (
    HTTPRedirect,
    MKAuthException,
    MKGeneralException,
    MKMissingDataError,
    MKUserError,
)
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.node_visualization import get_topology_view_and_filters
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    make_javascript_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuSidePopup,
    PageMenuTopic,
)
from cmk.gui.pages import Page, page_registry, PageResult
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    declare_permission,
    permission_registry,
    permission_section_registry,
    PermissionSection,
)

# Can be used by plugins
from cmk.gui.plugins.dashboard.utils import (  # noqa: F401 # pylint: disable=unused-import
    ABCFigureDashlet,
    builtin_dashboards,
    copy_view_into_dashlet,
    dashboard_breadcrumb,
    DashboardConfig,
    DashboardName,
    Dashlet,
    dashlet_registry,
    dashlet_types,
    dashlet_vs_general_settings,
    DashletConfig,
    DashletHandleInputFunc,
    DashletId,
    DashletInputFunc,
    DashletRefreshAction,
    DashletRefreshInterval,
    DashletSize,
    DashletType,
    DashletTypeName,
    get_all_dashboards,
    get_permitted_dashboards,
    GROW,
    IFrameDashlet,
    MAX,
    save_all_dashboards,
)
from cmk.gui.plugins.metrics.html_render import default_dashlet_graph_render_options
from cmk.gui.plugins.views.utils import data_source_registry
from cmk.gui.plugins.visuals.utils import visual_info_registry, visual_type_registry, VisualType
from cmk.gui.type_defs import InfoName, SingleInfos, VisualContext
from cmk.gui.utils.html import HTML, HTMLInput
from cmk.gui.utils.ntop import is_ntop_configured
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, makeuri_contextless, urlencode
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    Transform,
    ValueSpec,
    ValueSpecValidateFunc,
)
from cmk.gui.views import ABCAjaxInitialFilters, view_choices
from cmk.gui.views.datasource_selection import show_create_view_dialog
from cmk.gui.watolib.activate_changes import get_pending_changes_info, get_pending_changes_tooltip

loaded_with_language: Union[None, bool, str] = False

# These settings might go into the config module, sometime in future,
# in order to allow the user to customize this.

dashlet_padding = (
    26,
    4,
    4,
    4,
    4,
)  # Margin (N, E, S, W, N w/o title) between outer border of dashlet and its content
raster = 10  # Raster the dashlet coords are measured in (px)


@visual_type_registry.register
class VisualTypeDashboards(VisualType):
    @property
    def ident(self) -> str:
        return "dashboards"

    @property
    def title(self) -> str:
        return _("dashboard")

    @property
    def plural_title(self):
        return _("dashboards")

    @property
    def ident_attr(self):
        return "name"

    @property
    def multicontext_links(self):
        return False

    @property
    def show_url(self):
        return "dashboard.py"

    def page_menu_add_to_entries(self, add_type: str) -> Iterator[PageMenuEntry]:
        if not user.may("general.edit_dashboards"):
            return

        if add_type in ["availability", "graph_collection"]:
            return

        for name, board in get_permitted_dashboards().items():
            yield PageMenuEntry(
                title=board["title"],
                icon_name="dashboard",
                item=make_javascript_link(
                    "cmk.popup_menu.add_to_visual('dashboards', %s)" % json.dumps(name)
                ),
            )

    def add_visual_handler(self, target_visual_name, add_type, context, parameters):
        if not user.may("general.edit_dashboards"):
            # Exceptions do not work here.
            return

        if add_type == "pnpgraph" and context is None:
            # Raw Edition graphs are added correctly by htdocs/js/checkmk.js create_pnp_graph().
            # Enterprise Edition graphs:
            #
            # Context will always be None here, but the specification (in parameters)
            # will contain it. Transform the data to the format needed by the dashlets.
            #
            # Example:
            # parameters = [ 'template', {'service_description': 'CPU load', 'site': 'mysite',
            #                         'graph_index': 0, 'host_name': 'server123'}])
            specification = parameters["definition"]["specification"]
            if specification[0] == "template":
                context = {
                    "host": {"host": specification[1]["host_name"]},
                    # The service context has to be set, even for host graphs. Otherwise the
                    # pnpgraph dashlet would complain about missing context information when
                    # displaying host graphs.
                    "service": {"service": specification[1]["service_description"]},
                }
                parameters = {"source": specification[1]["graph_id"]}

            elif specification[0] == "custom":
                # Override the dashlet type here. It would be better to get the
                # correct dashlet type from the menu. But this does not seem to
                # be a trivial change.
                add_type = "custom_graph"
                context = {}
                parameters = {
                    "custom_graph": specification[1],
                }
            elif specification[0] == "combined":
                add_type = "combined_graph"
                parameters = copy.deepcopy(specification[1])
                parameters["graph_render_options"] = default_dashlet_graph_render_options
                context = parameters.pop("context", {})
                single_infos = specification[1]["single_infos"]
                if "host" in single_infos:
                    context["host"] = {"host": context.get("host")}
                if "service" in single_infos:
                    context["service"] = {"service": context.get("service")}
                parameters["single_infos"] = []

            else:
                raise MKGeneralException(
                    _(
                        "Graph specification '%s' is insuficient for Dashboard. "
                        "Please save your graph as a custom graph first, then "
                        "add that one to the dashboard."
                    )
                    % specification[0]
                )

        permitted_dashboards = get_permitted_dashboards()
        dashboard = _load_dashboard_with_cloning(permitted_dashboards, target_visual_name)

        dashlet_spec = default_dashlet_definition(add_type)

        dashlet_spec["context"] = context
        if add_type == "view":
            view_name = parameters["name"]
        else:
            dashlet_spec.update(parameters)

        # When a view shal be added to the dashboard, load the view and put it into the dashlet
        # FIXME: Mave this to the dashlet plugins
        if add_type == "view":
            # save the original context and override the context provided by the view
            context = dashlet_spec["context"]
            copy_view_into_dashlet(
                dashlet_spec, len(dashboard["dashlets"]), view_name, add_context=context
            )

        elif add_type in ["pnpgraph", "custom_graph"]:
            # The "add to visual" popup does not provide a timerange information,
            # but this is not an optional value. Set it to 25h initially.
            dashlet_spec.setdefault("timerange", "25h")

        add_dashlet(dashlet_spec, dashboard)

        # Directly go to the dashboard in edit mode. We send the URL as an answer
        # to the AJAX request
        response.set_data("OK dashboard.py?name=" + target_visual_name + "&edit=1")

    def load_handler(self):
        pass

    @property
    def permitted_visuals(self):
        return get_permitted_dashboards()


@permission_section_registry.register
class PermissionSectionDashboard(PermissionSection):
    @property
    def name(self) -> str:
        return "dashboard"

    @property
    def title(self) -> str:
        return _("Dashboards")

    @property
    def do_sort(self):
        return True


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()

    # Load plugins for dashboards. Currently these files
    # just may add custom dashboards by adding to builtin_dashboards.
    utils.load_web_plugins("dashboard", globals())

    _transform_old_dict_based_dashlets()

    visuals.declare_visual_permissions("dashboards", _("dashboards"))

    # Declare permissions for all dashboards
    for name, board in builtin_dashboards.items():
        # Special hack for the "main" dashboard: It contains graphs that are only correct in case
        # you are permitted on all hosts and services. All elements on the dashboard are filtered by
        # the individual user permissions. Only the problem graphs are not able to respect these
        # permissions. To not confuse the users we make the "main" dashboard in the enterprise
        # editions only visible to the roles that have the "general.see_all" permission.
        if name == "main" and not cmk_version.is_raw_edition():
            # Please note: This permitts the following roles: ["admin", "guest"]. Even if the user
            # overrides the permissions of these builtin roles in his configuration , this can not
            # be respected here. This is because the config of the user is not loaded yet. The user
            # would have to manually adjust the permissions on the main dashboard on his own.
            default_permissions = permission_registry["general.see_all"].defaults
        else:
            default_permissions = builtin_role_ids

        declare_permission(
            "dashboard.%s" % name,
            board["title"],
            board.get("description", ""),
            default_permissions,
        )

    # Make sure that custom views also have permissions
    declare_dynamic_permissions(lambda: visuals.declare_custom_permissions("dashboards"))


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.
    """
    # Needs to be a local import to not influence the regular plugin loading order
    import cmk.gui.plugins.dashboard as api_module
    import cmk.gui.plugins.dashboard.utils as plugin_utils

    for name in (
        "ABCFigureDashlet",
        "builtin_dashboards",
        "Dashlet",
        "dashlet_registry",
        "dashlet_types",
        "GROW",
        "IFrameDashlet",
        "MAX",
    ):
        api_module.__dict__[name] = plugin_utils.__dict__[name]


class LegacyDashlet(IFrameDashlet):
    """Helper to be able to handle pre 1.6 dashlet_type declared dashlets"""

    _type_name: DashletTypeName = ""
    _spec: DashletConfig = {}

    @classmethod
    def type_name(cls) -> str:
        return cls._type_name

    @classmethod
    def title(cls) -> str:
        return cls._spec["title"]

    @classmethod
    def description(cls) -> str:
        return cls._spec["description"]

    @classmethod
    def sort_index(cls) -> int:
        return cls._spec["sort_index"]

    @classmethod
    def single_infos(cls) -> SingleInfos:
        return cls._spec.get("single_infos", [])

    @classmethod
    def is_selectable(cls) -> bool:
        return cls._spec.get("selectable", True)

    @classmethod
    def is_resizable(cls) -> bool:
        return cls._spec.get("resizable", True)

    @classmethod
    def is_iframe_dashlet(cls) -> bool:
        return "iframe_render" in cls._spec or "iframe_urlfunc" in cls._spec

    @classmethod
    def initial_size(cls) -> DashletSize:
        return cls._spec.get("size", Dashlet.minimum_size)

    @classmethod
    def vs_parameters(
        cls,
    ) -> Union[
        None, List[DictionaryEntry], ValueSpec, Tuple[DashletInputFunc, DashletHandleInputFunc]
    ]:
        return cls._spec.get("parameters", None)

    @classmethod
    def opt_parameters(cls) -> Union[bool, List[str]]:
        """List of optional parameters in case vs_parameters() returns a list"""
        return cls._spec.get("opt_params", False)

    @classmethod
    def validate_parameters_func(cls) -> Optional[ValueSpecValidateFunc[Any]]:
        """Optional validation function in case vs_parameters() returns a list"""
        return cls._spec.get("validate_params")

    @classmethod
    def initial_refresh_interval(cls) -> DashletRefreshInterval:
        return cls._spec.get("refresh", False)

    @classmethod
    def allowed_roles(cls) -> List[str]:
        return cls._spec.get("allowed", builtin_role_ids)

    @classmethod
    def styles(cls) -> Optional[str]:
        return cls._spec.get("styles")

    @classmethod
    def script(cls) -> Optional[str]:
        return cls._spec.get("script")

    @classmethod
    def add_url(cls) -> str:
        if "add_urlfunc" in cls._spec:
            return cls._spec["add_urlfunc"]()
        return super().add_url()

    def infos(self) -> SingleInfos:
        return self._spec.get("infos", [])

    def default_display_title(self) -> str:
        return self._spec.get("title_func", lambda _arg: self.title)(self._dashlet_spec)

    def on_resize(self) -> Optional[str]:
        on_resize_func = self._spec.get("on_resize")
        if on_resize_func:
            return on_resize_func(self._dashlet_id, self._dashlet_spec)
        return None

    def on_refresh(self) -> Optional[str]:
        on_refresh_func = self._spec.get("on_refresh")
        if on_refresh_func:
            return on_refresh_func(self._dashlet_id, self._dashlet_spec)
        return None

    def update(self) -> None:
        if self.is_iframe_dashlet():
            self._spec["iframe_render"](self._dashlet_id, self._dashlet_spec)
        else:
            self._spec["render"](self._dashlet_id, self._dashlet_spec)

    def show(self) -> None:
        if "render" in self._spec:
            self._spec["render"](self._dashlet_id, self._dashlet_spec)

        elif self.is_iframe_dashlet():
            self._show_initial_iframe_container()

    def _get_iframe_url(self) -> Optional[str]:
        if not self.is_iframe_dashlet():
            return None

        if "iframe_urlfunc" in self._spec:
            # Optional way to render a dynamic iframe URL
            url = self._spec["iframe_urlfunc"](self._dashlet_spec)
            return url

        return super()._get_iframe_url()


# Pre Checkmk 1.6 the dashlets were declared with dictionaries like this:
#
# dashlet_types["hoststats"] = {
#     "title"       : _("Host statistics"),
#     "sort_index"  : 45,
#     "description" : _("Displays statistics about host states as globe and a table."),
#     "render"      : dashlet_hoststats,
#     "refresh"     : 60,
#     "allowed"     : builtin_role_ids,
#     "size"        : (30, 18),
#     "resizable"   : False,
# }
#
# Convert it to objects to be compatible
# TODO: Deprecate this one day.
def _transform_old_dict_based_dashlets() -> None:
    for dashlet_type_id, dashlet_spec in dashlet_types.items():

        @dashlet_registry.register
        class LegacyDashletType(LegacyDashlet):
            _type_name = dashlet_type_id
            _spec = dashlet_spec

        # help pylint
        _it_is_really_used = LegacyDashletType  # noqa: F841


# HTML page handler for generating the (a) dashboard. The name
# of the dashboard to render is given in the HTML variable 'name'.
@cmk.gui.pages.register("dashboard")
def page_dashboard() -> None:
    name = request.get_ascii_input_mandatory("name", "")
    if not name:
        name = _get_default_dashboard_name()
        request.set_var("name", name)  # make sure that URL context is always complete
    draw_dashboard(name)


def _get_default_dashboard_name() -> str:
    """Return the default dashboard name for the current site

    We separate our users into two groups:

    1. Those WITH the permission "see all hosts / service". Which are mainly administrative users.

    These are starting with the main overview dashboard which either shows a site drill down snapin
    (in case multiple sites are configured) or the hosts of their site (in case there is only a
    single site configured).

    2. Those WITHOUT the permission "see all hosts / service". Which are normal users.

    They will see the dashboard that has been built for operators and is built to show only the host
    and service problems that are relevant for the user.
    """
    if cmk_version.is_raw_edition():
        return "main"  # problems = main in raw edition
    return "main" if user.may("general.see_all") and user.may("dashboard.main") else "problems"


def _load_dashboard_with_cloning(
    permitted_dashboards: Dict[DashboardName, DashboardConfig],
    name: DashboardName,
    edit: bool = True,
) -> DashboardConfig:

    all_dashboards = get_all_dashboards()
    board = visuals.get_permissioned_visual(
        name, html.request.get_str_input("owner"), "dashboard", permitted_dashboards, all_dashboards
    )
    if edit and board["owner"] == "":
        # Trying to edit a builtin dashboard results in doing a copy
        active_user = user.id
        assert active_user is not None
        board = copy.deepcopy(board)
        board["owner"] = active_user
        board["public"] = False

        all_dashboards[(active_user, name)] = board
        permitted_dashboards[name] = board
        save_all_dashboards()

    return board


# Actual rendering function
def draw_dashboard(name: DashboardName) -> None:
    mode = "display"
    if request.var("edit") == "1":
        mode = "edit"

    if mode == "edit" and not user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = _load_dashboard_with_cloning(get_permitted_dashboards(), name, edit=mode == "edit")
    board = _add_context_to_dashboard(board)

    # Like _dashboard_info_handler we assume that only host / service filters are relevant
    board_context = visuals.active_context_from_request(["host", "service"], board["context"])
    board["context"] = board_context

    title = visuals.visual_title("dashboard", board, board_context)

    if not board.get("show_title"):
        # Remove the whole header line
        html.render_headfoot = False

    # In case we have a dashboard / dashlet that requires context information that is not available
    # yet, display a message to the user to insert the missing information.
    missing_mandatory_context_filters = visuals.missing_context_filters(
        set(board["mandatory_context_filters"]), board["context"]
    )

    dashlets = _get_dashlets(name, board)

    missing_single_infos: Set[InfoName] = set()
    unconfigured_single_infos: Set[InfoName] = set()
    for dashlet in dashlets:
        missing_single_infos.update(dashlet.missing_single_infos())
        unconfigured_single_infos.update(dashlet.unconfigured_single_infos())

    html.add_body_css_class("dashboard")
    breadcrumb = dashboard_breadcrumb(name, board, title)
    make_header(
        html,
        title,
        breadcrumb=breadcrumb,
        page_menu=_page_menu(
            breadcrumb, name, board, board_context, unconfigured_single_infos, mode
        ),
    )

    html.open_div(class_=["dashboard_%s" % name], id_="dashboard")  # Container of all dashlets

    dashlet_javascripts(board)
    dashlet_styles(board)

    for dashlet in dashlets:
        dashlet_title, content = _render_dashlet(
            board,
            dashlet,
            is_update=False,
            mtime=board["mtime"],
        )

        # Now after the dashlet content has been calculated render the whole dashlet
        with dashlet_container(dashlet):
            draw_dashlet(dashlet, content, dashlet_title)

    # Display the dialog during initial rendering when required context information is missing.
    if missing_single_infos or missing_mandatory_context_filters:
        html.final_javascript("cmk.page_menu.open_popup('popup_filters');")

    html.close_div()

    dashboard_properties = {
        "MAX": MAX,
        "GROW": GROW,
        "grid_size": raster,
        "dashlet_padding": dashlet_padding,
        "dashlet_min_size": Dashlet.minimum_size,
        "refresh_dashlets": _get_refresh_dashlets(dashlets),
        "on_resize_dashlets": _get_resize_dashlets(dashlets),
        "dashboard_name": name,
        "dashboard_mtime": board["mtime"],
        "dashlets": _get_dashlet_coords(dashlets),
        "slim_editor_thresholds": {
            "width": 28,
            "height": 14,
        },
    }

    html.javascript(
        """
cmk.dashboard.set_dashboard_properties(%s);
cmk.dashboard.calculate_dashboard();
window.onresize = function () { cmk.dashboard.calculate_dashboard(); }
cmk.page_menu.register_on_toggle_suggestions_handler(cmk.dashboard.calculate_dashboard);
cmk.dashboard.execute_dashboard_scheduler(1);
cmk.dashboard.register_event_handlers();
    """
        % json.dumps(dashboard_properties)
    )

    if mode == "edit":
        html.javascript("cmk.dashboard.toggle_dashboard_edit()")

    html.body_end()  # omit regular footer with status icons, etc.


def _get_dashlets(name: DashboardName, board: DashboardConfig) -> List[Dashlet]:
    """Return dashlet instances of the dashboard"""
    dashlets: List[Dashlet] = []
    for nr, dashlet_spec in enumerate(board["dashlets"]):
        try:
            dashlet_type = get_dashlet_type(dashlet_spec)
            dashlet = dashlet_type(name, board, nr, dashlet_spec)
        except KeyError as e:
            info_text = (
                _(
                    "Dashlet type %s could not be found. "
                    "Please remove it from your dashboard configuration."
                )
                % e
            )
            dashlet = _fallback_dashlet(name, board, dashlet_spec, nr, info_text=info_text)
        except Exception:
            dashlet = _fallback_dashlet(name, board, dashlet_spec, nr)

        dashlets.append(dashlet)

    return dashlets


def _get_refresh_dashlets(
    dashlets: List[Dashlet],
) -> List[Tuple[DashletId, DashletRefreshInterval, DashletRefreshAction]]:
    """Return information for dashlets with automatic refresh"""
    refresh_dashlets = []
    for dashlet in dashlets:
        refresh = get_dashlet_refresh(dashlet)
        if refresh:
            refresh_dashlets.append(refresh)
    return refresh_dashlets


def _get_resize_dashlets(dashlets: List[Dashlet]) -> Dict[DashletId, str]:
    """Get list of javascript functions to execute after resizing the dashlets"""
    on_resize_dashlets: Dict[DashletId, str] = {}
    for dashlet in dashlets:
        on_resize = get_dashlet_on_resize(dashlet)
        if on_resize:
            on_resize_dashlets[dashlet.dashlet_id] = on_resize
    return on_resize_dashlets


def _get_dashlet_coords(dashlets: List[Dashlet]) -> List[Dict[str, int]]:
    """Return a list of all dashlets dimensions and positions"""
    return [get_dashlet_dimensions(dashlet) for dashlet in dashlets]


@contextmanager
def dashlet_container(dashlet: Dashlet) -> Iterator[None]:
    classes = ["dashlet", dashlet.type_name()]
    if dashlet.is_resizable():
        classes.append("resizable")

    html.open_div(id_="dashlet_%d" % dashlet.dashlet_id, class_=classes)
    try:
        yield
    finally:
        html.close_div()


def _render_dashlet(
    board: DashboardConfig, dashlet: Dashlet, is_update: bool, mtime: int
) -> Tuple[Union[str, HTML], HTMLInput]:
    content: HTMLInput = ""
    title: Union[str, HTML] = ""
    missing_infos = visuals.missing_context_filters(
        set(board["mandatory_context_filters"]), board["context"]
    )
    missing_infos.update(dashlet.missing_single_infos())
    try:
        if missing_infos:
            return (
                _("Filter context missing"),
                str(
                    html.render_warning(
                        _(
                            "Unable to render this element, "
                            "because we miss some required context information (%s). Please update the "
                            "form on the right to make this element render."
                        )
                        % ", ".join(sorted(missing_infos))
                    )
                ),
            )

        title = dashlet.render_title_html()
        content = _render_dashlet_content(board, dashlet, is_update=is_update, mtime=board["mtime"])

    except Exception as e:
        content = render_dashlet_exception_content(dashlet, e)

    return title, content


def _render_dashlet_content(
    board: DashboardConfig, dashlet: Dashlet, is_update: bool, mtime: int
) -> str:
    with output_funnel.plugged():
        if is_update:
            dashlet.update()
        else:
            dashlet.show()

        if mtime < board["mtime"]:
            # prevent reloading on the dashboard which already has the current mtime,
            # this is normally the user editing this dashboard. All others: reload
            # the whole dashboard once.
            html.javascript(
                "if (cmk.dashboard.dashboard_properties.dashboard_mtime < %d) {\n"
                "    parent.location.reload();\n"
                "}" % board["mtime"]
            )

        return output_funnel.drain()


def render_dashlet_exception_content(dashlet: Dashlet, e: Exception) -> HTMLInput:
    if isinstance(e, MKMissingDataError):
        return html.render_message(str(e))

    if not isinstance(e, MKUserError):
        # Do not write regular error messages related to normal user interaction and validation to
        # the web.log
        logger.exception(
            "Problem while rendering dashboard element %d of type %s",
            dashlet.dashlet_id,
            dashlet.type_name(),
        )

    with output_funnel.plugged():
        if isinstance(e, MKException):
            html.show_error(
                _(
                    "Problem while rendering dashboard element %d of type %s: %s. Have a look at "
                    "<tt>var/log/web.log</tt> for further information."
                )
                % (dashlet.dashlet_id, dashlet.type_name(), str(e))
            )
            return output_funnel.drain()

        crash_handler.handle_exception_as_gui_crash_report(
            details={
                "dashlet_id": dashlet.dashlet_id,
                "dashlet_type": dashlet.type_name(),
                "dashlet_spec": dashlet.dashlet_spec,
            }
        )
        return output_funnel.drain()


def _fallback_dashlet(
    name: DashboardName,
    board: DashboardConfig,
    dashlet_spec: DashletConfig,
    dashlet_id: int,
    info_text: str = "",
) -> Dashlet:
    """Create some place holder dashlet instance in case the dashlet could not be
    initialized"""
    dashlet_spec = dashlet_spec.copy()
    dashlet_spec.update({"type": "nodata", "text": info_text})

    dashlet_type = get_dashlet_type(dashlet_spec)
    return dashlet_type(name, board, dashlet_id, dashlet_spec)


def _get_mandatory_filters(
    board: DashboardConfig, unconfigured_single_infos: Set[str]
) -> Iterable[str]:

    # Get required single info keys (the ones that are not set by the config)
    for info_key in unconfigured_single_infos:
        for info, _unused in visuals.visual_info_registry[info_key]().single_spec:
            yield info

    # Get required context filters set in the dashboard config
    yield from board["mandatory_context_filters"]


def _page_menu(
    breadcrumb: Breadcrumb,
    name: DashboardName,
    board: DashboardConfig,
    board_context: VisualContext,
    unconfigured_single_infos: Set[str],
    mode: str,
) -> PageMenu:

    html.close_ul()
    menu = PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="dashboard",
                title=_("Dashboard"),
                topics=[
                    PageMenuTopic(
                        title=_("Edit"),
                        entries=list(_dashboard_edit_entries(name, board, mode)),
                    ),
                    PageMenuTopic(
                        title=_("User profile"),
                        entries=[
                            PageMenuEntry(
                                title=_("Set as start URL"),
                                icon_name="home",
                                item=make_javascript_link(
                                    "cmk.dashboard.set_start_url(%s)" % json.dumps(name)
                                ),
                            )
                        ],
                    ),
                ],
            ),
            PageMenuDropdown(
                name="add_dashlets",
                title=_("Add"),
                topics=list(_page_menu_topics(name)),
                is_enabled=True,
            ),
            PageMenuDropdown(
                name="dashboards",
                title=_("Dashboards"),
                topics=list(_page_menu_dashboards(name)),
                is_enabled=True,
            ),
        ],
        breadcrumb=breadcrumb,
        has_pending_changes=bool(get_pending_changes_info()),
        pending_changes_tooltip=get_pending_changes_tooltip(),
    )

    _extend_display_dropdown(menu, board, board_context, unconfigured_single_infos)

    return menu


def _page_menu_dashboards(name) -> Iterable[PageMenuTopic]:
    if cmk_version.is_raw_edition():
        linked_dashboards = ["main", "checkmk"]  # problems = main in raw edition
    else:
        linked_dashboards = ["main", "problems", "checkmk"]

    yield PageMenuTopic(
        title=_("Related Dashboards"),
        entries=list(_dashboard_related_entries(name, linked_dashboards)),
    )
    yield PageMenuTopic(
        title=_("Other Dashboards"),
        entries=list(_dashboard_other_entries(name, linked_dashboards)),
    )
    yield PageMenuTopic(
        title=_("Customize"),
        entries=[
            PageMenuEntry(
                title=_("Customize Dashboards"),
                icon_name="dashboard",
                item=make_simple_link("edit_dashboards.py"),
            )
        ]
        if user.may("general.edit_dashboards")
        else [],
    )


def _page_menu_topics(name: DashboardName) -> Iterator[PageMenuTopic]:

    yield PageMenuTopic(
        title=_("Views"),
        entries=list(_dashboard_add_views_dashlet_entries(name)),
    )

    yield PageMenuTopic(
        title=_("Graphs"),
        entries=list(_dashboard_add_graphs_dashlet_entries(name)),
    )

    yield PageMenuTopic(
        title=_("Metrics"),
        entries=list(_dashboard_add_metrics_dashlet_entries(name)),
    )

    yield PageMenuTopic(
        title=_("State"),
        entries=list(_dashboard_add_state_dashlet_entries(name)),
    )

    yield PageMenuTopic(
        title=_("Inventory"),
        entries=list(_dashboard_add_inventory_dashlet_entries(name)),
    )

    yield PageMenuTopic(
        title=_("Checkmk"),
        entries=list(_dashboard_add_checkmk_dashlet_entries(name)),
    )

    if is_ntop_configured():
        yield PageMenuTopic(
            title=_("Ntop"),
            entries=list(_dashboard_add_ntop_dashlet_entries(name)),
        )

    yield PageMenuTopic(
        title=_("Other"),
        entries=list(_dashboard_add_other_dashlet_entries(name)),
    )


def _dashboard_edit_entries(
    name: DashboardName, board: DashboardConfig, mode: str
) -> Iterator[PageMenuEntry]:
    if not user.may("general.edit_dashboards"):
        return

    if board["owner"] == "":
        # Not owned dashboards must be cloned before being able to edit. Do not switch to
        # edit mode using javascript, use the URL with edit=1. When this URL is opened,
        # the dashboard will be cloned for this user
        yield PageMenuEntry(
            title=_("Customize builtin dashboard"),
            icon_name="edit",
            item=make_simple_link(makeuri(request, [("edit", 1)])),
        )
        return

    if board["owner"] != user.id:
        return

    edit_text = _("Leave layout mode")
    display_text = _("Enter layout mode")

    yield PageMenuEntry(
        title=edit_text if mode == "edit" else display_text,
        icon_name={
            "icon": "dashboard_edit",
            "emblem": "disable" if mode == "edit" else "trans",
        },
        item=make_javascript_link(
            'cmk.dashboard.toggle_dashboard_edit("%s", "%s")' % (edit_text, display_text)
        ),
        is_shortcut=True,
        is_suggested=False,
        name="toggle_edit",
        sort_index=99,
    )

    yield PageMenuEntry(
        title=_("Properties"),
        icon_name="configuration",
        item=make_simple_link(
            makeuri_contextless(
                request,
                [
                    ("load_name", name),
                    ("back", urlencode(makeuri(request, []))),
                ],
                filename="edit_dashboard.py",
            )
        ),
    )


def _dashboard_other_entries(
    name: str,
    linked_dashboards: Iterable[str],
) -> Iterable[PageMenuEntry]:
    ntop_not_configured = not is_ntop_configured()
    for dashboard_name, dashboard in get_permitted_dashboards().items():
        if name in linked_dashboards and dashboard_name in linked_dashboards:
            continue
        if dashboard["hidden"]:
            continue
        if ntop_not_configured and dashboard_name.startswith("ntop_"):
            continue

        yield PageMenuEntry(
            title=dashboard["title"],
            icon_name=dashboard["icon"] or "dashboard",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("name", dashboard_name)],
                    filename="dashboard.py",
                )
            ),
        )


def _dashboard_related_entries(
    name: str,
    linked_dashboards: Iterable[str],
) -> Iterable[PageMenuEntry]:
    if name not in linked_dashboards:
        return  # only the three main dashboards are related

    dashboards = get_permitted_dashboards()
    for entry_name in linked_dashboards:
        if entry_name not in dashboards:
            continue
        dashboard = dashboards[entry_name]
        yield PageMenuEntry(
            title=dashboard["title"],
            icon_name=dashboard["icon"] or "unknown",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("name", entry_name)],
                    filename="dashboard.py",
                )
            ),
            is_shortcut=True,
            is_suggested=False,
            is_enabled=name != entry_name,
        )


def _minimal_context(
    mandatory_filters: Iterable[str], known_context: VisualContext
) -> VisualContext:
    filter_context: VisualContext = {name: {} for name in mandatory_filters}
    return visuals.get_merged_context(filter_context, known_context)


def _extend_display_dropdown(
    menu: PageMenu,
    board: DashboardConfig,
    board_context: VisualContext,
    unconfigured_single_infos: Set[str],
) -> None:
    display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())

    minimal_context = _minimal_context(
        _get_mandatory_filters(board, unconfigured_single_infos), board_context
    )
    # Like _dashboard_info_handler we assume that only host / service filters are relevant
    info_list = ["host", "service"]

    display_dropdown.topics.insert(
        0,
        PageMenuTopic(
            title=_("Filter"),
            entries=[
                PageMenuEntry(
                    title=_("Filter"),
                    icon_name="filter",
                    item=PageMenuSidePopup(
                        visuals.render_filter_form(
                            info_list,
                            minimal_context,
                            board["name"],
                            "ajax_initial_dashboard_filters",
                        )
                    ),
                    name="filters",
                    is_shortcut=True,
                    is_suggested=False,
                ),
            ],
        ),
    )


@page_registry.register_page("ajax_initial_dashboard_filters")
class AjaxInitialDashboardFilters(ABCAjaxInitialFilters):
    def _get_context(self, page_name: str) -> VisualContext:
        dashboard_name = page_name
        board = _load_dashboard_with_cloning(get_permitted_dashboards(), dashboard_name, edit=False)
        board = _add_context_to_dashboard(board)

        # For the topology dashboard filters are retrieved from a corresponding view context
        if page_name == "topology":
            _view, show_filters = get_topology_view_and_filters()
            return {
                f.ident: board["context"].get(f.ident, {}) for f in show_filters if f.available()
            }

        return _minimal_context(_get_mandatory_filters(board, set()), board["context"])


@dataclass
class PageMenuEntryCEEOnly(PageMenuEntry):
    def __post_init__(self) -> None:
        if cmk_version.is_raw_edition():
            self.is_enabled = False
            self.disabled_tooltip = _("Enterprise feature")


def _dashboard_add_dashlet_back_http_var() -> Tuple[str, str]:
    return "back", makeuri(request, [("edit", "1")])


def _dashboard_add_view_dashlet_link(
    name: DashboardName,
    create: Literal["0", "1"],
    filename: str,
) -> PageMenuLink:
    return make_simple_link(
        makeuri_contextless(
            request,
            [
                ("name", name),
                ("create", create),
                _dashboard_add_dashlet_back_http_var(),
            ],
            filename=filename,
        )
    )


def _dashboard_add_views_dashlet_entries(name: DashboardName) -> Iterable[PageMenuEntry]:

    yield PageMenuEntry(
        title=_("New view"),
        icon_name="view",
        item=_dashboard_add_view_dashlet_link(name, "1", "create_view_dashlet.py"),
    )

    yield PageMenuEntry(
        title=_("Link to existing view"),
        icon_name="view_link",
        item=_dashboard_add_view_dashlet_link(name, "0", "create_link_view_dashlet.py"),
    )

    yield PageMenuEntry(
        title=_("Copy of existing view"),
        icon_name="view_copy",
        item=_dashboard_add_view_dashlet_link(name, "0", "create_view_dashlet.py"),
    )


def _dashboard_add_non_view_dashlet_link(
    name: DashboardName,
    dashlet_type: str,
) -> PageMenuLink:
    return make_simple_link(
        makeuri_contextless(
            request,
            [
                ("name", name),
                ("create", "0"),
                _dashboard_add_dashlet_back_http_var(),
                ("type", dashlet_type),
            ],
            filename="edit_dashlet.py",
        )
    )


def _dashboard_add_graphs_dashlet_entries(name: DashboardName) -> Iterable[PageMenuEntry]:

    yield PageMenuEntryCEEOnly(
        title="Single metric graph",
        icon_name={
            "icon": "graph",
            "emblem": "add",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "single_timeseries"),
    )

    yield PageMenuEntry(
        title=_("Performance graph"),
        icon_name="graph",
        item=_dashboard_add_non_view_dashlet_link(name, "pnpgraph"),
    )

    yield PageMenuEntryCEEOnly(
        title=_("Custom graph"),
        icon_name={
            "icon": "graph",
            "emblem": "add",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "custom_graph"),
    )

    yield PageMenuEntryCEEOnly(
        title=_("Combined graph"),
        icon_name={
            "icon": "graph",
            "emblem": "add",  # TODO: Need its own icon
        },
        item=_dashboard_add_non_view_dashlet_link(name, "combined_graph"),
    )


def _dashboard_add_state_dashlet_entries(name: DashboardName) -> Iterable[PageMenuEntryCEEOnly]:

    yield PageMenuEntryCEEOnly(
        title="Host State",
        icon_name="host_state",
        item=_dashboard_add_non_view_dashlet_link(name, "state_host"),
    )

    yield PageMenuEntryCEEOnly(
        title="Service State",
        icon_name="service_state",
        item=_dashboard_add_non_view_dashlet_link(name, "state_service"),
    )

    yield PageMenuEntryCEEOnly(
        title="Host state summary",
        icon_name={
            "icon": "host_state",
            "emblem": "statistic",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "host_state_summary"),
    )

    yield PageMenuEntryCEEOnly(
        title="Service state summary",
        icon_name={
            "icon": "service_state",
            "emblem": "statistic",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "service_state_summary"),
    )


def _dashboard_add_inventory_dashlet_entries(name: DashboardName) -> Iterable[PageMenuEntryCEEOnly]:

    yield PageMenuEntryCEEOnly(
        title="Host Inventory",
        icon_name="inventory",
        item=_dashboard_add_non_view_dashlet_link(name, "inventory"),
    )


def _dashboard_add_metrics_dashlet_entries(name: DashboardName) -> Iterable[PageMenuEntryCEEOnly]:

    yield PageMenuEntryCEEOnly(
        title="Average scatterplot",
        icon_name="scatterplot",
        item=_dashboard_add_non_view_dashlet_link(name, "average_scatterplot"),
    )

    yield PageMenuEntryCEEOnly(
        title="Barplot",
        icon_name="barplot",
        item=_dashboard_add_non_view_dashlet_link(name, "barplot"),
    )

    yield PageMenuEntryCEEOnly(
        title="Gauge",
        icon_name="gauge",
        item=_dashboard_add_non_view_dashlet_link(name, "gauge"),
    )

    yield PageMenuEntryCEEOnly(
        title="Single metric",
        icon_name="single_metric",
        item=_dashboard_add_non_view_dashlet_link(name, "single_metric"),
    )


def _dashboard_add_checkmk_dashlet_entries(name: DashboardName) -> Iterable[PageMenuEntry]:

    yield PageMenuEntryCEEOnly(
        title="Site overview",
        icon_name="site_overview",
        item=_dashboard_add_non_view_dashlet_link(name, "site_overview"),
    )

    yield PageMenuEntryCEEOnly(
        title="Alert statistics",
        icon_name={"icon": "alerts", "emblem": "statistic"},
        item=_dashboard_add_non_view_dashlet_link(name, "alert_statistics"),
    )
    yield PageMenuEntry(
        title="Host statistics",
        icon_name={
            "icon": "folder",
            "emblem": "statistic",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "hoststats"),
    )

    yield PageMenuEntry(
        title="Service statistics",
        icon_name={
            "icon": "services",
            "emblem": "statistic",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "servicestats"),
    )

    yield PageMenuEntry(
        title="Event statistics",
        icon_name={
            "icon": "event_console",
            "emblem": "statistic",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "eventstats"),
    )

    yield PageMenuEntryCEEOnly(
        title="Notification timeline",
        icon_name={
            "icon": "notifications",
            "emblem": "statistic",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "notifications_bar_chart"),
    )

    yield PageMenuEntryCEEOnly(
        title="Alert timeline",
        icon_name={
            "icon": "alerts",
            "emblem": "statistic",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "alerts_bar_chart"),
    )

    yield PageMenuEntryCEEOnly(
        title=_("Percentage of service problems"),
        icon_name={"icon": "graph", "emblem": "statistic"},
        item=_dashboard_add_non_view_dashlet_link(name, "problem_graph"),
    )

    yield PageMenuEntry(
        title="User messages",
        icon_name="notifications",
        item=_dashboard_add_non_view_dashlet_link(name, "user_messages"),
    )

    yield PageMenuEntry(
        title="Sidebar element",
        icon_name="custom_snapin",
        item=_dashboard_add_non_view_dashlet_link(name, "snapin"),
        is_show_more=True,
    )


def _dashboard_add_ntop_dashlet_entries(name: DashboardName) -> Iterable[PageMenuEntryCEEOnly]:

    yield PageMenuEntryCEEOnly(
        title="Alerts",
        icon_name={
            "icon": "ntop",
            "emblem": "warning",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "ntop_alerts"),
    )

    yield PageMenuEntryCEEOnly(
        title="Flows",
        icon_name={
            "icon": "ntop",
            "emblem": "more",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "ntop_flows"),
    )

    yield PageMenuEntryCEEOnly(
        title="Top talkers",
        icon_name={
            "icon": "ntop",
            "emblem": "statistic",
        },
        item=_dashboard_add_non_view_dashlet_link(name, "ntop_top_talkers"),
    )


def _dashboard_add_other_dashlet_entries(name: DashboardName) -> Iterable[PageMenuEntry]:

    yield PageMenuEntry(
        title="Custom URL",
        icon_name="dashlet_url",
        item=_dashboard_add_non_view_dashlet_link(name, "url"),
        is_show_more=True,
    )

    yield PageMenuEntry(
        title="Static text",
        icon_name="dashlet_nodata",
        item=_dashboard_add_non_view_dashlet_link(name, "nodata"),
        is_show_more=True,
    )


# Render dashlet custom scripts
def dashlet_javascripts(board):
    scripts = "\n".join([ty.script() for ty in used_dashlet_types(board) if ty.script()])
    if scripts:
        html.javascript(scripts)


# Render dashlet custom styles
def dashlet_styles(board):
    styles = "\n".join([ty.styles() for ty in used_dashlet_types(board) if ty.styles()])
    if styles:
        html.style(styles)


def used_dashlet_types(board):
    type_names = list({d["type"] for d in board["dashlets"]})
    return [dashlet_registry[ty] for ty in type_names if ty in dashlet_registry]


# dashlets using the 'url' method will be refreshed by us. Those
# dashlets using static content (such as an iframe) will not be
# refreshed by us but need to do that themselves.
# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_refresh(
    dashlet: Dashlet,
) -> Optional[Tuple[DashletId, DashletRefreshInterval, DashletRefreshAction]]:
    if dashlet.type_name() == "url" or (
        not dashlet.is_iframe_dashlet() and dashlet.refresh_interval()
    ):
        refresh = dashlet.refresh_interval()
        if not refresh:
            return None

        action = dashlet.get_refresh_action()
        if action:
            return (dashlet.dashlet_id, refresh, action)
    return None


# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_on_resize(dashlet: Dashlet) -> Optional[str]:
    on_resize = dashlet.on_resize()
    if on_resize:
        return "(function() {%s})" % on_resize
    return None


# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_dimensions(dashlet: Dashlet) -> Dict[str, int]:
    dimensions = {}
    dimensions["x"], dimensions["y"] = dashlet.position()
    dimensions["w"], dimensions["h"] = dashlet.size()
    return dimensions


def get_dashlet_type(dashlet_spec: DashletConfig) -> Type[Dashlet]:
    return dashlet_registry[dashlet_spec["type"]]


def get_dashlet(board: DashboardName, ident: DashletId) -> DashletConfig:
    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    try:
        return dashboard["dashlets"][ident]
    except IndexError:
        raise MKGeneralException(_("The dashboard element does not exist."))


def draw_dashlet(dashlet: Dashlet, content: HTMLInput, title: Union[str, HTML]) -> None:
    """Draws the initial HTML code for one dashlet

    Each dashlet has an id "dashlet_%d", where %d is its index (in
    board["dashlets"]).  Javascript uses that id for the resizing. Within that
    div there is an inner div containing the actual dashlet content. This content
    is updated later using the dashboard_dashlet.py ajax call.
    """
    if all(
        (
            not isinstance(dashlet, ABCFigureDashlet),
            title is not None,
            dashlet.show_title(),
        )
    ):
        title_background = ["highlighted"] if dashlet.show_title() is True else []
        html.div(
            HTMLWriter.render_span(title),
            id_="dashlet_title_%d" % dashlet.dashlet_id,
            class_=["title"] + title_background,
        )

    css = ["dashlet_inner"]
    if dashlet.show_background():
        css.append("background")

    html.open_div(id_="dashlet_inner_%d" % dashlet.dashlet_id, class_=css)
    html.write_html(HTML(content))
    html.close_div()


# .
#   .--Draw Dashlet--------------------------------------------------------.
#   |     ____                       ____            _     _      _        |
#   |    |  _ \ _ __ __ ___      __ |  _ \  __ _ ___| |__ | | ___| |_      |
#   |    | | | | '__/ _` \ \ /\ / / | | | |/ _` / __| '_ \| |/ _ \ __|     |
#   |    | |_| | | | (_| |\ V  V /  | |_| | (_| \__ \ | | | |  __/ |_      |
#   |    |____/|_|  \__,_| \_/\_/   |____/ \__,_|___/_| |_|_|\___|\__|     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Draw dashlet HTML code which are rendered by the multisite dashboard |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("dashboard_dashlet")
def ajax_dashlet() -> None:
    name = request.get_ascii_input_mandatory("name", "")
    if not name:
        raise MKUserError("name", _("The name of the dashboard is missing."))

    try:
        board = get_permitted_dashboards()[name]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    board = _add_context_to_dashboard(board)
    board_context = visuals.active_context_from_request(["host", "service"], board["context"])
    board["context"] = board_context

    ident = request.get_integer_input_mandatory("id")
    dashlet_spec = next(
        dashlet_spec for nr, dashlet_spec in enumerate(board["dashlets"]) if nr == ident
    )

    if not dashlet_spec:
        raise MKUserError("id", _("The element can not be found on the dashboard."))

    if dashlet_spec["type"] not in dashlet_registry:
        raise MKUserError("id", _("The requested element type does not exist."))

    mtime = request.get_integer_input_mandatory("mtime", 0)

    dashlet = None
    try:
        dashlet_type = get_dashlet_type(dashlet_spec)
        dashlet = dashlet_type(name, board, ident, dashlet_spec)
        _title, content = _render_dashlet(board, dashlet, is_update=True, mtime=mtime)
    except Exception as e:
        if dashlet is None:
            dashlet = _fallback_dashlet(name, board, dashlet_spec, ident)
        content = render_dashlet_exception_content(dashlet, e)

    html.write_html(HTML(content))


def _add_context_to_dashboard(board: DashboardConfig) -> DashboardConfig:
    board = copy.deepcopy(board)
    board.setdefault("single_infos", [])
    board.setdefault("context", {})
    board.setdefault("mandatory_context_filters", [])
    return board


# .
#   .--Dashboard List------------------------------------------------------.
#   |           ____            _     _        _     _     _               |
#   |          |  _ \  __ _ ___| |__ | |__    | |   (_)___| |_             |
#   |          | | | |/ _` / __| '_ \| '_ \   | |   | / __| __|            |
#   |          | |_| | (_| \__ \ | | | |_) |  | |___| \__ \ |_             |
#   |          |____/ \__,_|___/_| |_|_.__(_) |_____|_|___/\__|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("edit_dashboards")
def page_edit_dashboards() -> None:
    visuals.page_list(
        what="dashboards",
        title=_("Edit Dashboards"),
        visuals=get_all_dashboards(),
        render_custom_buttons=_render_dashboard_buttons,
    )


def _render_dashboard_buttons(dashboard_name: DashboardName, dashboard: DashboardConfig) -> None:
    if dashboard["owner"] == user.id:
        html.icon_button(
            makeuri_contextless(
                request,
                [
                    ("name", dashboard_name),
                    ("edit", "1"),
                ],
                "dashboard.py",
            ),
            title=_("Edit dashboard"),
            icon="dashboard",
        )


# .
#   .--Create Dashb.-------------------------------------------------------.
#   |      ____                _         ____            _     _           |
#   |     / ___|_ __ ___  __ _| |_ ___  |  _ \  __ _ ___| |__ | |__        |
#   |    | |   | '__/ _ \/ _` | __/ _ \ | | | |/ _` / __| '_ \| '_ \       |
#   |    | |___| | |  __/ (_| | ||  __/ | |_| | (_| \__ \ | | | |_) |      |
#   |     \____|_|  \___|\__,_|\__\___| |____/ \__,_|___/_| |_|_.__(_)     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | When clicking on create dashboard, this page is opened to make the   |
#   | context type of the new dashboard selectable.                        |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("create_dashboard")
def page_create_dashboard() -> None:
    visuals.page_create_visual("dashboards", visual_info_registry.keys())


# .
#   .--Dashb. Config-------------------------------------------------------.
#   |     ____            _     _         ____             __ _            |
#   |    |  _ \  __ _ ___| |__ | |__     / ___|___  _ __  / _(_) __ _      |
#   |    | | | |/ _` / __| '_ \| '_ \   | |   / _ \| '_ \| |_| |/ _` |     |
#   |    | |_| | (_| \__ \ | | | |_) |  | |__| (_) | | | |  _| | (_| |     |
#   |    |____/ \__,_|___/_| |_|_.__(_)  \____\___/|_| |_|_| |_|\__, |     |
#   |                                                           |___/      |
#   +----------------------------------------------------------------------+
#   | Configures the global settings of a dashboard.                       |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("edit_dashboard")
def page_edit_dashboard() -> None:
    visuals.page_edit_visual(
        "dashboards",
        get_all_dashboards(),
        create_handler=create_dashboard,
        custom_field_handler=dashboard_fields_handler,
        info_handler=_dashboard_info_handler,
        help_text_context=_(
            "A dashboard can have an optional context. It can for example be restricted to display "
            "only information of a single host or for a set of services matching a regular "
            "expression."
        ),
    )


def _dashboard_info_handler(visual):
    # We could use all available infos here, but there is a lot of normally unused stuff. For better
    # usability reduce the list to the (assumed) relevant used ones.
    return ["host", "service"]


def dashboard_fields_handler(dashboard: DashboardConfig) -> None:
    _vs_dashboard().render_input("dashboard", dashboard and dashboard or None)


def create_dashboard(old_dashboard: DashboardConfig, dashboard: DashboardConfig) -> DashboardConfig:
    vs_dashboard = _vs_dashboard()
    board_properties = vs_dashboard.from_html_vars("dashboard")
    vs_dashboard.validate_value(board_properties, "dashboard")
    dashboard.update(board_properties)

    # Do not remove the dashlet configuration during general property editing
    dashboard["dashlets"] = old_dashboard.get("dashlets", [])
    dashboard["mtime"] = int(time.time())

    return dashboard


def _vs_dashboard() -> Dictionary:
    return Dictionary(
        title=_("Dashboard Properties"),
        render="form",
        optional_keys=False,
        elements=[
            (
                "show_title",
                Checkbox(
                    title=_("Display dashboard title"),
                    label=_("Show the header of the dashboard with the configured title."),
                    default_value=True,
                ),
            ),
            (
                "mandatory_context_filters",
                visuals.FilterChoices(
                    # Like _dashboard_info_handler we assume that only host / service filters are relevant
                    infos=["host", "service"],
                    title=_("Required context filters"),
                    help=_(
                        "Show the dialog that can be used to update the dashboard context "
                        "on initial dashboard rendering and enforce the user to provide the "
                        "context filters that are set here. This can be useful in case you want "
                        "the users to first provide some context before rendering the dashboard."
                    ),
                ),
            ),
        ],
        form_isopen=False,
        help=_(
            "Here, you can configure additional properties of the dashboard. This is completely "
            "optional and only needed to create more advanced dashboards. For example, you can "
            "make certain filters mandatory. This enables you to build generic dashboards which "
            "could for example contain all the relevant information for a single Oracle DB. "
            "However, before the dashboard is rendered, the user has to decide which DB he wants "
            "to look at."
        ),
    )


# .
#   .--Dashlet Editor------------------------------------------------------.
#   |    ____            _     _      _     _____    _ _ _                 |
#   |   |  _ \  __ _ ___| |__ | | ___| |_  | ____|__| (_) |_ ___  _ __     |
#   |   | | | |/ _` / __| '_ \| |/ _ \ __| |  _| / _` | | __/ _ \| '__|    |
#   |   | |_| | (_| \__ \ | | | |  __/ |_  | |__| (_| | | || (_) | |       |
#   |   |____/ \__,_|___/_| |_|_|\___|\__| |_____\__,_|_|\__\___/|_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


@cmk.gui.pages.register("create_link_view_dashlet")
def page_create_link_view_dashlet() -> None:
    """Choose an existing view from the list of available views"""
    name = request.get_str_input_mandatory("name")
    choose_view(name, _("Embed existing view"), _create_linked_view_dashlet_spec)


def _create_linked_view_dashlet_spec(dashlet_id: int, view_name: str) -> Dict:
    dashlet_spec = default_dashlet_definition("linked_view")
    dashlet_spec["name"] = view_name
    return dashlet_spec


@cmk.gui.pages.register("create_view_dashlet")
def page_create_view_dashlet() -> None:
    create = request.var("create", "1") == "1"
    name = request.get_str_input_mandatory("name")

    if create:
        url = makeuri(
            request,
            [("back", makeuri(request, []))],
            filename="create_view_dashlet_infos.py",
        )
        show_create_view_dialog(next_url=url)

    else:
        # Choose an existing view from the list of available views
        choose_view(name, _("Copy existing view"), _create_cloned_view_dashlet_spec)


def _create_cloned_view_dashlet_spec(dashlet_id: int, view_name: str) -> Dict:
    dashlet_spec = default_dashlet_definition("view")

    # save the original context and override the context provided by the view
    copy_view_into_dashlet(dashlet_spec, dashlet_id, view_name)
    return dashlet_spec


@cmk.gui.pages.register("create_view_dashlet_infos")
def page_create_view_dashlet_infos() -> None:
    ds_name = request.get_str_input_mandatory("datasource")
    if ds_name not in data_source_registry:
        raise MKUserError("datasource", _("The given datasource is not supported"))

    # Create a new view by choosing the datasource and the single object types
    visuals.page_create_visual(
        "views",
        data_source_registry[ds_name]().infos,
        next_url=makeuri_contextless(
            request,
            [
                ("name", request.var("name")),
                ("type", "view"),
                ("datasource", ds_name),
                ("back", makeuri(request, [])),
                (
                    "next",
                    makeuri_contextless(
                        request,
                        [("name", request.var("name")), ("edit", "1")],
                        "dashboard.py",
                    ),
                ),
            ],
            filename="edit_dashlet.py",
        ),
    )


def choose_view(name: DashboardName, title: str, create_dashlet_spec_func: Callable) -> None:
    vs_view = DropdownChoice(
        title=_("View name"),
        choices=lambda: view_choices(allow_empty=False),
        sorted=True,
        no_preselect_title="",
    )

    try:
        dashboard = get_permitted_dashboards()[name]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    breadcrumb = _dashlet_editor_breadcrumb(name, dashboard, title)
    make_header(
        html,
        title,
        breadcrumb=breadcrumb,
        page_menu=_choose_view_page_menu(breadcrumb),
    )

    if request.var("_save") and transactions.check_transaction():
        try:
            view_name = vs_view.from_html_vars("view")
            vs_view.validate_value(view_name, "view")

            dashlet_id = len(dashboard["dashlets"])
            dashlet_spec = create_dashlet_spec_func(dashlet_id, view_name)
            add_dashlet(dashlet_spec, dashboard)

            raise HTTPRedirect(
                makeuri_contextless(
                    request,
                    [
                        ("name", name),
                        ("id", str(dashlet_id)),
                        ("back", request.get_url_input("back")),
                    ],
                    filename="edit_dashlet.py",
                )
            )
        except MKUserError as e:
            html.user_error(e)

    html.begin_form("choose_view")
    forms.header(_("Select view"))
    forms.section(vs_view.title())
    vs_view.render_input("view", None)
    html.help(vs_view.help())
    forms.end()

    html.hidden_fields()
    html.end_form()
    html.footer()


def _choose_view_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    return make_simple_form_page_menu(
        _("View"),
        breadcrumb,
        form_name="choose_view",
        button_name="_save",
        save_title=_("Continue"),
    )


@page_registry.register_page("edit_dashlet")
class EditDashletPage(Page):
    def __init__(self) -> None:
        if not user.may("general.edit_dashboards"):
            raise MKAuthException(_("You are not allowed to edit dashboards."))

        self._board = request.get_str_input_mandatory("name")
        self._ident = request.get_integer_input("id")

        try:
            self._dashboard = get_permitted_dashboards()[self._board]
        except KeyError:
            raise MKUserError("name", _("The requested dashboard does not exist."))

    def page(self) -> PageResult:  # pylint: disable=useless-return,too-many-branches
        if self._ident is None:
            type_name = request.get_str_input_mandatory("type")
            mode = "add"

            try:
                dashlet_type = dashlet_registry[type_name]
            except KeyError:
                raise MKUserError("type", _("The requested element type does not exist."))

            title = _("Add element: %s") % dashlet_type.title()

            # Initial configuration
            dashlet_spec: DashletConfig = {
                "position": dashlet_type.initial_position(),
                "size": dashlet_type.initial_size(),
                "single_infos": dashlet_type.single_infos(),
                "type": type_name,
            }
            dashlet_spec.update(dashlet_type.default_settings())

            if dashlet_type.has_context():
                dashlet_spec["context"] = {}

            self._ident = len(self._dashboard["dashlets"])

            single_infos_raw = request.var("single_infos")
            single_infos: SingleInfos = []
            if single_infos_raw:
                single_infos = single_infos_raw.split(",")
                for key in single_infos:
                    if key not in visual_info_registry:
                        raise MKUserError("single_infos", _("The info %s does not exist.") % key)

            if not single_infos:
                single_infos = dashlet_type.single_infos()

            dashlet_spec["single_infos"] = single_infos
        else:
            mode = "edit"

            try:
                dashlet_spec = self._dashboard["dashlets"][self._ident]
            except IndexError:
                raise MKUserError("id", _("The element does not exist."))

            type_name = dashlet_spec["type"]
            dashlet_type = dashlet_registry[type_name]
            single_infos = dashlet_spec["single_infos"]

            title = _("Edit element: %s") % dashlet_type.title()

        breadcrumb = _dashlet_editor_breadcrumb(self._board, self._dashboard, title)
        make_header(
            html,
            title,
            breadcrumb=breadcrumb,
            page_menu=_dashlet_editor_page_menu(breadcrumb),
        )

        vs_general = dashlet_vs_general_settings(dashlet_type, single_infos)

        def dashlet_info_handler(dashlet_spec: DashletConfig) -> SingleInfos:
            assert isinstance(self._ident, int)
            dashlet_type = dashlet_registry[dashlet_spec["type"]]
            dashlet = dashlet_type(self._board, self._dashboard, self._ident, dashlet_spec)
            return dashlet.infos()

        context_specs = visuals.get_context_specs(dashlet_spec, info_handler=dashlet_info_handler)

        vs_type: Optional[ValueSpec] = None
        params = dashlet_type.vs_parameters()
        render_input_func = None
        handle_input_func = None
        if isinstance(params, list):
            # TODO: Refactor all params to be a Dictionary() and remove this special case
            vs_type = Dictionary(
                title=_("Properties"),
                render="form",
                optional_keys=dashlet_type.opt_parameters(),
                validate=dashlet_type.validate_parameters_func(),
                elements=params,
            )

        elif isinstance(params, (Dictionary, Transform)):
            vs_type = params

        elif isinstance(params, tuple):
            # It's a tuple of functions which should be used to render and parse the params
            render_input_func, handle_input_func = params

        # Check disjoint option on known valuespecs
        if isinstance(vs_type, Dictionary):
            settings_elements = set(el[0] for el in vs_general._get_elements())
            properties_elements = set(el[0] for el in vs_type._get_elements())
            assert settings_elements.isdisjoint(
                properties_elements
            ), "Dashboard element settings and properties have a shared option name"

        if request.var("_save") and transactions.transaction_valid():
            try:
                general_properties = vs_general.from_html_vars("general")
                vs_general.validate_value(general_properties, "general")
                dashlet_spec.update(general_properties)

                # Remove unset optional attributes
                optional_properties = set(e[0] for e in vs_general._get_elements()) - set(
                    vs_general._required_keys
                )
                for option in optional_properties:
                    if option not in general_properties and option in dashlet_spec:
                        del dashlet_spec[option]

                if vs_type:
                    type_properties = vs_type.from_html_vars("type")
                    vs_type.validate_value(type_properties, "type")
                    dashlet_spec.update(type_properties)

                elif handle_input_func:
                    # The returned dashlet must be equal to the parameter! It is not replaced/re-added
                    # to the dashboard object. FIXME TODO: Clean this up!
                    dashlet_spec = handle_input_func(self._ident, dashlet_spec)

                if context_specs:
                    dashlet_spec["context"] = visuals.process_context_specs(context_specs)

                if mode == "add":
                    self._dashboard["dashlets"].append(dashlet_spec)

                save_all_dashboards()
                html.footer()
                raise HTTPRedirect(request.get_url_input("next", request.get_url_input("back")))

            except MKUserError as e:
                html.user_error(e)

        html.begin_form("dashlet", method="POST")
        vs_general.render_input("general", dashlet_spec)
        visuals.render_context_specs(dashlet_spec, context_specs)

        if vs_type:
            vs_type.render_input("type", dashlet_spec)
        elif render_input_func:
            render_input_func(dashlet_spec)

        forms.end()
        html.show_localization_hint()
        html.hidden_fields()
        html.end_form()

        html.footer()
        return None


def _dashlet_editor_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    return make_simple_form_page_menu(
        _("Element"), breadcrumb, form_name="dashlet", button_name="_save"
    )


def _dashlet_editor_breadcrumb(name: str, board: DashboardConfig, title: str) -> Breadcrumb:
    breadcrumb = make_topic_breadcrumb(
        mega_menu_registry.menu_monitoring(),
        PagetypeTopics.get_topic(board["topic"]).title(),
    )
    breadcrumb.append(
        BreadcrumbItem(
            visuals.visual_title("dashboard", board, {}),
            request.get_url_input("back"),
        )
    )

    breadcrumb.append(make_current_page_breadcrumb_item(title))

    return breadcrumb


@cmk.gui.pages.register("clone_dashlet")
def page_clone_dashlet() -> None:
    if not user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = request.var("name")
    if not board:
        raise MKUserError("name", _("The name of the dashboard is missing."))

    ident = request.get_integer_input_mandatory("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    try:
        dashlet_spec = dashboard["dashlets"][ident]
    except IndexError:
        raise MKUserError("id", _("The element does not exist."))

    new_dashlet_spec = dashlet_spec.copy()
    dashlet_type = get_dashlet_type(new_dashlet_spec)
    new_dashlet_spec["position"] = dashlet_type.initial_position()

    dashboard["dashlets"].append(new_dashlet_spec)
    dashboard["mtime"] = int(time.time())
    save_all_dashboards()

    raise HTTPRedirect(request.get_url_input("back"))


@cmk.gui.pages.register("delete_dashlet")
def page_delete_dashlet() -> None:
    if not user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = request.var("name")
    if not board:
        raise MKUserError("name", _("The name of the dashboard is missing."))

    ident = request.get_integer_input_mandatory("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    try:
        _dashlet_spec = dashboard["dashlets"][ident]  # noqa: F841
    except IndexError:
        raise MKUserError("id", _("The element does not exist."))

    dashboard["dashlets"].pop(ident)
    dashboard["mtime"] = int(time.time())
    save_all_dashboards()

    raise HTTPRedirect(request.get_url_input("back"))


# .
#   .--Ajax Updater--------------------------------------------------------.
#   |       _     _              _   _           _       _                 |
#   |      / \   (_) __ ___  __ | | | |_ __   __| | __ _| |_ ___ _ __      |
#   |     / _ \  | |/ _` \ \/ / | | | | '_ \ / _` |/ _` | __/ _ \ '__|     |
#   |    / ___ \ | | (_| |>  <  | |_| | |_) | (_| | (_| | ||  __/ |        |
#   |   /_/   \_\/ |\__,_/_/\_\  \___/| .__/ \__,_|\__,_|\__\___|_|        |
#   |          |__/                   |_|                                  |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_ajax_update() -> Tuple[DashletConfig, DashboardConfig]:
    if not user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = request.get_str_input_mandatory("name")
    ident = request.get_integer_input_mandatory("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    try:
        dashlet_spec = dashboard["dashlets"][ident]
    except IndexError:
        raise MKUserError("id", _("The element does not exist."))

    return dashlet_spec, dashboard


@cmk.gui.pages.register("ajax_dashlet_pos")
def ajax_dashlet_pos() -> None:
    dashlet_spec, board = check_ajax_update()

    board["mtime"] = int(time.time())

    dashlet_spec["position"] = (
        request.get_integer_input_mandatory("x"),
        request.get_integer_input_mandatory("y"),
    )
    dashlet_spec["size"] = (
        request.get_integer_input_mandatory("w"),
        request.get_integer_input_mandatory("h"),
    )
    save_all_dashboards()
    response.set_data("OK %d" % board["mtime"])


# .
#   .--Dashlet Popup-------------------------------------------------------.
#   |   ____            _     _      _     ____                            |
#   |  |  _ \  __ _ ___| |__ | | ___| |_  |  _ \ ___  _ __  _   _ _ __     |
#   |  | | | |/ _` / __| '_ \| |/ _ \ __| | |_) / _ \| '_ \| | | | '_ \    |
#   |  | |_| | (_| \__ \ | | | |  __/ |_  |  __/ (_) | |_) | |_| | |_) |   |
#   |  |____/ \__,_|___/_| |_|_|\___|\__| |_|   \___/| .__/ \__,_| .__/    |
#   |                                                |_|         |_|       |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


# TODO: Move this to the Dashlet class
def default_dashlet_definition(ty: DashletTypeName) -> DashletConfig:
    return {
        "type": ty,
        "position": dashlet_registry[ty].initial_position(),
        "size": dashlet_registry[ty].initial_size(),
        "show_title": True,
    }


def add_dashlet(dashlet_spec: DashletConfig, dashboard: DashboardConfig) -> None:
    dashboard["dashlets"].append(dashlet_spec)
    dashboard["mtime"] = int(time.time())
    save_all_dashboards()
