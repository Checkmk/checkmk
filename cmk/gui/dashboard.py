#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import copy
import json
from typing import Set, Dict, Optional, Tuple, Type, List, Union, Callable, Iterator

from six import ensure_str

import cmk.utils.version as cmk_version
from cmk.gui.utils.html import HTML
from cmk.utils.exceptions import MKException

import cmk.gui.pages
import cmk.gui.notify as notify
import cmk.gui.config as config
import cmk.gui.visuals as visuals
import cmk.gui.forms as forms
import cmk.gui.utils as utils
import cmk.gui.crash_reporting as crash_reporting
from cmk.gui.type_defs import InfoName, VisualContext
from cmk.gui.valuespec import (
    Transform,
    Dictionary,
    TextUnicode,
    DropdownChoice,
    Checkbox,
    FixedValue,
)
from cmk.gui.valuespec import ValueSpec, ValueSpecValidateFunc, DictionaryEntry
import cmk.gui.i18n
from cmk.gui.i18n import _u, _
from cmk.gui.log import logger
from cmk.gui.globals import html
from cmk.gui.main_menu import MegaMenuMonitoring
from cmk.gui.breadcrumb import make_main_menu_breadcrumb, Breadcrumb, BreadcrumbItem
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    PageMenuPopup,
    make_simple_link,
    make_javascript_link,
    make_display_options_dropdown,
)

from cmk.gui.exceptions import (
    HTTPRedirect,
    MKGeneralException,
    MKAuthException,
    MKUserError,
)
from cmk.gui.permissions import (
    declare_permission,
    permission_section_registry,
    PermissionSection,
)
from cmk.gui.plugins.visuals.utils import (
    visual_info_registry,
    visual_type_registry,
    VisualType,
)

import cmk.gui.plugins.dashboard

if not cmk_version.is_raw_edition():
    import cmk.gui.cee.plugins.dashboard  # pylint: disable=no-name-in-module

if cmk_version.is_managed_edition():
    import cmk.gui.cme.plugins.dashboard  # pylint: disable=no-name-in-module

from cmk.gui.plugins.views.utils import data_source_registry
from cmk.gui.plugins.dashboard.utils import (
    builtin_dashboards,
    GROW,
    MAX,
    dashlet_types,
    dashlet_registry,
    Dashlet,
    get_all_dashboards,
    save_all_dashboards,
    get_permitted_dashboards,
    copy_view_into_dashlet,
)
# Can be used by plugins
from cmk.gui.plugins.dashboard.utils import (  # noqa: F401 # pylint: disable=unused-import
    DashletType, DashletTypeName, DashletRefreshInterval, DashletRefreshAction, DashletConfig,
    DashboardConfig, DashboardName, DashletSize, DashletInputFunc, DashletHandleInputFunc,
    DashletId,
)

loaded_with_language: Union[None, bool, str] = False

# These settings might go into the config module, sometime in future,
# in order to allow the user to customize this.

screen_margin = 12  # Distance from the left border of the main-frame to the dashboard area
dashlet_padding = 34, 4, -2, 4, 4  # Margin (N, E, S, W, N w/o title) between outer border of dashlet and its content
#dashlet_padding  = 23, 2, 2, 2, 2 # Margin (N, E, S, W, N w/o title) between outer border of dashlet and its content
raster = 10  # Raster the dashlet coords are measured in (px)


@visual_type_registry.register
class VisualTypeDashboards(VisualType):
    @property
    def ident(self):
        return "dashboards"

    @property
    def title(self):
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
        if not config.user.may("general.edit_dashboards"):
            return

        if add_type in ["availability", "graph_collection"]:
            return

        for name, board in get_permitted_dashboards().items():
            yield PageMenuEntry(
                title=board["title"],
                icon_name="dashboard",
                item=make_javascript_link("cmk.popup_menu.add_to_visual('dashboards', %s)" %
                                          json.dumps(name)),
            )

    def add_visual_handler(self, target_visual_name, add_type, context, parameters):
        if not config.user.may("general.edit_dashboards"):
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
                context = {"host": specification[1]["host_name"]}
                if specification[1].get("service_description") != "_HOST_":
                    context["service"] = specification[1]["service_description"]
                parameters = {"source": specification[1]["graph_index"] + 1}

            elif specification[0] == "custom":
                # Override the dashlet type here. It would be better to get the
                # correct dashlet type from the menu. But this does not seem to
                # be a trivial change.
                add_type = "custom_graph"
                context = {}
                parameters = {
                    "custom_graph": specification[1],
                }

            else:
                raise MKGeneralException(
                    _("Graph specification '%s' is insuficient for Dashboard. "
                      "Please save your graph as a custom graph first, then "
                      'add that one to the dashboard.') % specification[0])

        permitted_dashboards = get_permitted_dashboards()
        dashboard = _load_dashboard_with_cloning(permitted_dashboards, target_visual_name)

        dashlet = default_dashlet_definition(add_type)

        dashlet["context"] = context
        if add_type == 'view':
            view_name = parameters['name']
        else:
            dashlet.update(parameters)

        # When a view shal be added to the dashboard, load the view and put it into the dashlet
        # FIXME: Mave this to the dashlet plugins
        if add_type == 'view':
            # save the original context and override the context provided by the view
            context = dashlet['context']
            copy_view_into_dashlet(dashlet,
                                   len(dashboard['dashlets']),
                                   view_name,
                                   add_context=context)

        elif add_type in ["pnpgraph", "custom_graph"]:
            # The "add to visual" popup does not provide a timerange information,
            # but this is not an optional value. Set it to 25h initially.
            dashlet.setdefault("timerange", "1")

        add_dashlet(dashlet, dashboard)

        # Directly go to the dashboard in edit mode. We send the URL as an answer
        # to the AJAX request
        html.write('OK dashboard.py?name=' + target_visual_name + '&edit=1')

    def load_handler(self):
        pass

    @property
    def permitted_visuals(self):
        return get_permitted_dashboards()


@permission_section_registry.register
class PermissionSectionDashboard(PermissionSection):
    @property
    def name(self):
        return "dashboard"

    @property
    def title(self):
        return _("Dashboards")

    @property
    def do_sort(self):
        return True


# Load plugins in web/plugins/dashboard and declare permissions,
# note: these operations produce language-specific results and
# thus must be reinitialized everytime a language-change has
# been detected.
def load_plugins(force: bool) -> None:
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    # Load plugins for dashboards. Currently these files
    # just may add custom dashboards by adding to builtin_dashboards.
    utils.load_web_plugins("dashboard", globals())

    _transform_old_dict_based_dashlets()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()

    visuals.declare_visual_permissions('dashboards', _("dashboards"))

    # Declare permissions for all dashboards
    for name, board in builtin_dashboards.items():
        declare_permission(
            "dashboard.%s" % name,
            board["title"],
            board.get("description", ""),
            config.builtin_role_ids,
        )

    # Make sure that custom views also have permissions
    config.declare_dynamic_permissions(lambda: visuals.declare_custom_permissions('dashboards'))


class LegacyDashlet(cmk.gui.plugins.dashboard.IFrameDashlet):
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
    def single_infos(cls) -> List[str]:
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
        cls
    ) -> Union[None, List[DictionaryEntry], ValueSpec, Tuple[DashletInputFunc,
                                                             DashletHandleInputFunc]]:
        return cls._spec.get("parameters", None)

    @classmethod
    def opt_parameters(cls) -> Optional[List[DictionaryEntry]]:
        """List of optional parameters in case vs_parameters() returns a list"""
        return cls._spec.get("opt_params")

    @classmethod
    def validate_parameters_func(cls) -> Optional[ValueSpecValidateFunc]:
        """Optional validation function in case vs_parameters() returns a list"""
        return cls._spec.get("validate_params")

    @classmethod
    def initial_refresh_interval(cls) -> DashletRefreshInterval:
        return cls._spec.get("refresh", False)

    @classmethod
    def allowed_roles(cls) -> List[str]:
        return cls._spec.get("allowed", config.builtin_role_ids)

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
        return super(LegacyDashlet, cls).add_url()

    def infos(self) -> List[str]:
        return self._spec.get("infos", [])

    def display_title(self) -> str:
        title_func = self._spec.get("title_func")
        if title_func:
            return title_func(self._dashlet_spec)
        return self.title()

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
            self._spec['iframe_render'](self._dashlet_id, self._dashlet_spec)
        else:
            self._spec['render'](self._dashlet_id, self._dashlet_spec)

    def show(self) -> None:
        if "render" in self._spec:
            self._spec['render'](self._dashlet_id, self._dashlet_spec)

        elif self.is_iframe_dashlet():
            self._show_initial_iframe_container()

    def _get_iframe_url(self) -> Optional[str]:
        if not self.is_iframe_dashlet():
            return None

        if "iframe_urlfunc" in self._spec:
            # Optional way to render a dynamic iframe URL
            url = self._spec["iframe_urlfunc"](self._dashlet_spec)
            return url

        return super(LegacyDashlet, self)._get_iframe_url()


# Pre Check_MK 1.6 the dashlets were declared with dictionaries like this:
#
# dashlet_types["hoststats"] = {
#     "title"       : _("Host Statistics"),
#     "sort_index"  : 45,
#     "description" : _("Displays statistics about host states as globe and a table."),
#     "render"      : dashlet_hoststats,
#     "refresh"     : 60,
#     "allowed"     : config.builtin_role_ids,
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
# This defaults to "main".
@cmk.gui.pages.register("dashboard")
def page_dashboard() -> None:
    name = html.request.var("name")
    if not name:
        name = "main"
        html.request.set_var("name", name)  # make sure that URL context is always complete
    if name not in get_permitted_dashboards():
        raise MKUserError("name", _('The requested dashboard does not exist.'))

    draw_dashboard(name)


def _load_dashboard_with_cloning(permitted_dashboards: Dict[DashboardName, DashboardConfig],
                                 name: DashboardName,
                                 edit: bool = True) -> DashboardConfig:
    board = permitted_dashboards[name]
    if edit and board['owner'] != config.user.id:
        # This dashboard which does not belong to the current user is about to
        # be edited. In order to make this possible, the dashboard is being
        # cloned now!
        board = copy.deepcopy(board)
        board['owner'] = config.user.id
        board['public'] = False

        all_dashboards = get_all_dashboards()
        all_dashboards[(config.user.id, name)] = board
        permitted_dashboards[name] = board
        save_all_dashboards()

    return board


# Actual rendering function
def draw_dashboard(name: DashboardName) -> None:
    mode = 'display'
    if html.request.var('edit') == '1':
        mode = 'edit'

    if mode == 'edit' and not config.user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    permitted_dashboards = get_permitted_dashboards()
    board = _load_dashboard_with_cloning(permitted_dashboards, name, edit=mode == 'edit')
    board = _add_context_to_dashboard(board)

    # Like _dashboard_info_handler we assume that only host / service filters are relevant
    board_context = visuals.get_merged_context(
        visuals.get_context_from_uri_vars(["host", "service"], board["single_infos"]),
        board["context"])

    title = visuals.visual_title('dashboard', board)

    # Distance from top of the screen to the lower border of the heading
    header_height = 69

    if not board.get('show_title'):
        # Remove the whole header line
        html.set_render_headfoot(False)
        header_height = 0

    # In case we have a dashboard / dashlet that requires context information that is not available
    # yet, display a message to the user to insert the missing information.
    missing_single_infos: Set[InfoName] = set()
    unconfigured_single_infos: Set[InfoName] = set()
    missing_mandatory_context_filters = not set(board_context.keys()).issuperset(
        set(board["mandatory_context_filters"]))

    html.add_body_css_class("dashboard")
    breadcrumb = _dashboard_breadcrumb(name, title)
    html.header(title,
                breadcrumb=breadcrumb,
                page_menu=_page_menu(breadcrumb, name, board, board_context,
                                     unconfigured_single_infos, mode))

    html.open_div(class_=["dashboard_%s" % name], id_="dashboard")  # Container of all dashlets

    dashlet_javascripts(board)
    dashlet_styles(board)

    refresh_dashlets = []  # Dashlets with automatic refresh, for Javascript
    dashlet_coords = []  # Dimensions and positions of dashlet
    on_resize_dashlets = {}  # javascript function to execute after ressizing the dashlet
    for nr, dashlet in enumerate(board["dashlets"]):
        dashlet_content_html = u""
        dashlet_title_html = u""
        dashlet_instance = None
        try:
            dashlet_type = get_dashlet_type(dashlet)
            dashlet_instance = dashlet_type(name, board, nr, dashlet)

            unconfigured_single_infos.update(dashlet_instance.unconfigured_single_infos())
            missing_single_infos.update(dashlet_instance.missing_single_infos())

            if missing_single_infos or missing_mandatory_context_filters:
                continue  # Do not render in case required context information is missing

            refresh = get_dashlet_refresh(dashlet_instance)
            if refresh:
                refresh_dashlets.append(refresh)

            on_resize = get_dashlet_on_resize(dashlet_instance)
            if on_resize:
                on_resize_dashlets[nr] = on_resize

            dashlet_title_html = render_dashlet_title_html(dashlet_instance)
            dashlet_content_html = _render_dashlet_content(board,
                                                           dashlet_instance,
                                                           is_update=False,
                                                           mtime=board["mtime"])

        except Exception as e:
            if dashlet_instance is None:
                dashlet_instance = _fallback_dashlet_instance(name, board, dashlet, nr)
            dashlet_content_html = render_dashlet_exception_content(dashlet, nr, e)

        # Now after the dashlet content has been calculated render the whole dashlet
        dashlet_container_begin(nr, dashlet)
        draw_dashlet(dashlet_instance, dashlet_content_html, dashlet_title_html)
        dashlet_container_end()
        dashlet_coords.append(get_dashlet_dimensions(dashlet_instance))

    # Display the dialog during initial rendering when required context information is missing.
    if missing_single_infos or missing_mandatory_context_filters:
        html.final_javascript("cmk.page_menu.open_popup('popup_filters');")

    html.close_div()

    dashboard_properties = {
        "MAX": MAX,
        "GROW": GROW,
        "grid_size": raster,
        "header_height": header_height,
        "screen_margin": screen_margin,
        "dashlet_padding": dashlet_padding,
        "dashlet_min_size": Dashlet.minimum_size,
        "refresh_dashlets": refresh_dashlets,
        "on_resize_dashlets": on_resize_dashlets,
        "dashboard_name": name,
        "dashboard_mtime": board['mtime'],
        "dashlets": dashlet_coords,
    }

    html.javascript("""
cmk.dashboard.set_dashboard_properties(%s);
cmk.dashboard.calculate_dashboard();
window.onresize = function () { cmk.dashboard.calculate_dashboard(); }
cmk.dashboard.execute_dashboard_scheduler(1);
cmk.dashboard.register_event_handlers();
    """ % json.dumps(dashboard_properties))

    if mode == 'edit':
        html.javascript('cmk.dashboard.toggle_dashboard_edit()')

    html.body_end()  # omit regular footer with status icons, etc.


def _dashboard_breadcrumb(name: str, title: str) -> Breadcrumb:
    breadcrumb = make_main_menu_breadcrumb(MegaMenuMonitoring)

    breadcrumb.append(BreadcrumbItem(
        title,
        html.makeuri_contextless([("name", name)]),
    ))

    return breadcrumb


def dashlet_container_begin(nr: DashletId, dashlet: DashletConfig) -> None:
    dashlet_type = get_dashlet_type(dashlet)

    classes = ['dashlet', dashlet['type']]
    if dashlet_type.is_resizable():
        classes.append('resizable')

    html.open_div(id_="dashlet_%d" % nr, class_=classes)


def dashlet_container_end() -> None:
    html.close_div()


def render_dashlet_title_html(dashlet_instance: Dashlet) -> str:
    title = dashlet_instance.display_title()
    if title is not None and dashlet_instance.show_title():
        url = dashlet_instance.title_url()
        if url:
            title = u"%s" % html.render_a(_u(title), url)
        else:
            title = _u(title)
    return title


def _render_dashlet_content(board: DashboardConfig, dashlet_instance: Dashlet, is_update: bool,
                            mtime: int) -> str:

    # All outer variables are completely reset for the dashlets to have a clean, well known state.
    # The context that has been built based on the relevant HTTP variables is applied again.
    dashlet_context = dashlet_instance.context if dashlet_instance.has_context() else {}
    with visuals.context_uri_vars(dashlet_context, dashlet_instance.single_infos()):
        # Set some dashboard related variables that are needed by some dashlets
        html.request.set_var("name", dashlet_instance.dashboard_name)
        html.request.set_var("mtime", str(mtime))

        return _update_or_show(board, dashlet_instance, is_update, mtime)


def _update_or_show(board: DashboardConfig, dashlet_instance: Dashlet, is_update: bool,
                    mtime: int) -> str:
    with html.plugged():
        if is_update:
            dashlet_instance.update()
        else:
            dashlet_instance.show()

        if mtime < board['mtime']:
            # prevent reloading on the dashboard which already has the current mtime,
            # this is normally the user editing this dashboard. All others: reload
            # the whole dashboard once.
            html.javascript('if (cmk.dashboard.dashboard_properties.dashboard_mtime < %d) {\n'
                            '    parent.location.reload();\n'
                            '}' % board['mtime'])

        return html.drain()


def render_dashlet_exception_content(dashlet_spec: DashletConfig, dashlet_id: int,
                                     e: Exception) -> str:

    if not isinstance(e, MKUserError):
        # Do not write regular error messages related to normal user interaction and validation to
        # the web.log
        logger.exception("Problem while rendering dashlet %d of type %s", dashlet_id,
                         dashlet_spec["type"])

    with html.plugged():
        if isinstance(e, MKException):
            # Unify different string types from exception messages to a unicode string
            try:
                exc_txt = str(e)
            except UnicodeDecodeError:
                exc_txt = ensure_str(str(e))

            html.show_error(
                _("Problem while rendering dashlet %d of type %s: %s. Have a look at "
                  "<tt>var/log/web.log</tt> for further information.") %
                (dashlet_id, dashlet_spec["type"], exc_txt))
            return html.drain()

        crash_reporting.handle_exception_as_gui_crash_report(
            details={
                "dashlet_id": dashlet_id,
                "dashlet_type": dashlet_spec["type"],
                "dashlet_spec": dashlet_spec,
            })
        return html.drain()


def _fallback_dashlet_instance(name: DashboardName, board: DashboardConfig,
                               dashlet_spec: DashletConfig, dashlet_id: int) -> Dashlet:
    """Create some place holder dashlet instance in case the dashlet_instance could not be
    initialized"""
    dashlet_spec = dashlet_spec.copy()
    dashlet_spec.update({"type": "nodata", "text": ""})

    dashlet_type = get_dashlet_type(dashlet_spec)
    return dashlet_type(name, board, dashlet_id, dashlet_spec)


# TODO: Use new generic popup dialogs once they are merged from the current UX rework
# TODO: Synchronize this with the view mechanic
def _render_filter_form(board: DashboardConfig, board_context: VisualContext,
                        unconfigured_single_infos: Set[str]) -> str:
    with html.plugged():
        html.begin_form("dashboard_context_dialog", method="GET", add_transid=False)

        forms.header(_("Dashboard context"))

        try:
            # Configure required single info keys (the ones that are not set by the config)
            single_context_filters = []
            for info_key in unconfigured_single_infos:
                info = visuals.visual_info_registry[info_key]()

                for filter_name, valuespec in info.single_spec:
                    single_context_filters.append(filter_name)
                    forms.section(valuespec.title())
                    valuespec.render_input(filter_name, None)
            forms.section_close()

            # Configure required context filters set in the dashboard config
            if board["mandatory_context_filters"]:
                forms.section(_("Required context"))
                for filter_key in board["mandatory_context_filters"]:
                    valuespec = visuals.VisualFilter(filter_key)
                    valuespec.render_input(filter_key, board_context.get(filter_key))

            # Give the user the option to redefine filters configured in the dashboard config
            # and also give the option to add some additional filters
            forms.section(_("Additional context"))
            # Like _dashboard_info_handler we assume that only host / service filters are relevant
            vs_filters = visuals.VisualFilterList(info_list=["host", "service"],
                                                  ignore=board["mandatory_context_filters"] +
                                                  single_context_filters)
            vs_filters.render_input("", board_context)
        except Exception:
            crash_reporting.handle_exception_as_gui_crash_report()

        html.open_tr()
        html.open_td(colspan=2)
        html.button("_submit", _("Update"))
        html.close_td()
        html.close_tr()

        forms.end()

        html.hidden_fields()
        html.end_form()

        return html.drain()


def _page_menu(breadcrumb: Breadcrumb, name: DashboardName, board: DashboardConfig,
               board_context: VisualContext, unconfigured_single_infos: Set[str],
               mode: str) -> PageMenu:

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
                ],
            ),
            PageMenuDropdown(
                name="add_dashlets",
                title=_("Add dashlets"),
                topics=[
                    PageMenuTopic(
                        title=_("Dashlets"),
                        entries=list(_dashboard_add_dashlet_entries(name, board, mode)),
                    ),
                ],
                is_enabled=mode == "edit",
            ),
        ],
        breadcrumb=breadcrumb,
    )

    _extend_display_dropdown(menu, board, board_context, unconfigured_single_infos)

    return menu


def _dashboard_edit_entries(name: DashboardName, board: DashboardConfig,
                            mode: str) -> Iterator[PageMenuEntry]:
    if not config.user.may("general.edit_dashboards"):
        return

    if board['owner'] != config.user.id:
        # Not owned dashboards must be cloned before being able to edit. Do not switch to
        # edit mode using javascript, use the URL with edit=1. When this URL is opened,
        # the dashboard will be cloned for this user
        yield PageMenuEntry(
            title=_("Edit dashboard"),
            icon_name="edit",
            item=make_simple_link(html.makeuri([("edit", 1)])),
        )
        return

    yield PageMenuEntry(
        title=_("Toggle edit mode"),
        icon_name="trans",
        item=make_javascript_link("cmk.dashboard.toggle_dashboard_edit()"),
        is_shortcut=True,
        name="toggle_edit",
    )

    yield PageMenuEntry(
        title=_("Properties"),
        icon_name="properties",
        item=make_simple_link(
            html.makeuri_contextless(
                [
                    ("load_name", name),
                    ("back", html.urlencode(html.makeuri([]))),
                ],
                filename="edit_dashboard.py",
            )),
    )


def _extend_display_dropdown(menu: PageMenu, board: DashboardConfig, board_context: VisualContext,
                             unconfigured_single_infos: Set[str]) -> None:
    display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())

    display_dropdown.topics.insert(
        0,
        PageMenuTopic(title=_("Filter"),
                      entries=[
                          PageMenuEntry(
                              title=_("Filter"),
                              icon_name="filters",
                              item=PageMenuPopup(
                                  _render_filter_form(board, board_context,
                                                      unconfigured_single_infos)),
                              name="filters",
                              is_shortcut=True,
                          ),
                      ]))


def _dashboard_add_dashlet_entries(name: DashboardName, board: DashboardConfig,
                                   mode: str) -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_('Copy existing view'),
        icon_name="dashlet_view",
        item=make_simple_link(
            'create_view_dashlet.py?name=%s&create=0&back=%s' %
            (html.urlencode(name), html.urlencode(html.makeuri([('edit', '1')])))),
    )

    for ty, dashlet_type in sorted(dashlet_registry.items(), key=lambda x: x[1].sort_index()):
        if dashlet_type.is_selectable():
            yield PageMenuEntry(
                title=dashlet_type.title(),
                icon_name="dashlet_%s" % ty,
                item=make_simple_link(dashlet_type.add_url()),
            )


# Render dashlet custom scripts
def dashlet_javascripts(board):
    scripts = '\n'.join([ty.script() for ty in used_dashlet_types(board) if ty.script()])
    if scripts:
        html.javascript(scripts)


# Render dashlet custom styles
def dashlet_styles(board):
    styles = '\n'.join([ty.styles() for ty in used_dashlet_types(board) if ty.styles()])
    if styles:
        html.style(styles)


def used_dashlet_types(board):
    type_names = list({d['type'] for d in board['dashlets']})
    return [dashlet_registry[ty] for ty in type_names]


# dashlets using the 'url' method will be refreshed by us. Those
# dashlets using static content (such as an iframe) will not be
# refreshed by us but need to do that themselves.
# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_refresh(
    dashlet_instance: Dashlet
) -> Optional[Tuple[DashletId, DashletRefreshInterval, DashletRefreshAction]]:
    if dashlet_instance.type_name() == "url" or (not dashlet_instance.is_iframe_dashlet() and
                                                 dashlet_instance.refresh_interval()):
        refresh = dashlet_instance.refresh_interval()
        if not refresh:
            return None

        action = dashlet_instance.get_refresh_action()
        if action:
            return (dashlet_instance.dashlet_id, refresh, action)
    return None


# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_on_resize(dashlet_instance: Dashlet) -> Optional[str]:
    on_resize = dashlet_instance.on_resize()
    if on_resize:
        return '(function() {%s})' % on_resize
    return None


# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_dimensions(dashlet_instance: Dashlet) -> Dict[str, int]:
    dimensions = {}
    dimensions['x'], dimensions['y'] = dashlet_instance.position()
    dimensions['w'], dimensions['h'] = dashlet_instance.size()
    return dimensions


def get_dashlet_type(dashlet: DashletConfig) -> Type[Dashlet]:
    return dashlet_registry[dashlet["type"]]


def get_dashlet(board: DashboardName, ident: DashletId) -> DashletConfig:
    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _('The requested dashboard does not exist.'))

    try:
        return dashboard['dashlets'][ident]
    except IndexError:
        raise MKGeneralException(_('The dashlet does not exist.'))


def draw_dashlet(dashlet_instance: Dashlet, dashlet_content_html: str,
                 dashlet_title_html: str) -> None:
    """Draws the initial HTML code for one dashlet

    Each dashlet has an id "dashlet_%d", where %d is its index (in
    board["dashlets"]).  Javascript uses that id for the resizing. Within that
    div there is an inner div containing the actual dashlet content. This content
    is updated later using the dashboard_dashlet.py ajax call.
    """
    if dashlet_title_html is not None and dashlet_instance.show_title():
        html.div(html.render_span(dashlet_title_html),
                 id_="dashlet_title_%d" % dashlet_instance.dashlet_id,
                 class_=["title"])

    css = ["dashlet_inner"]
    if dashlet_instance.show_background():
        css.append("background")

    html.open_div(id_="dashlet_inner_%d" % dashlet_instance.dashlet_id, class_=css)
    html.write_html(HTML(dashlet_content_html))
    html.close_div()


#.
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
    name = html.request.var('name')
    if not name:
        raise MKUserError("name", _('The name of the dashboard is missing.'))

    ident = html.request.get_integer_input_mandatory("id")

    try:
        board = get_permitted_dashboards()[name]
    except KeyError:
        raise MKUserError("name", _('The requested dashboard does not exist.'))

    board = _add_context_to_dashboard(board)

    the_dashlet = None
    for nr, dashlet in enumerate(board['dashlets']):
        if nr == ident:
            the_dashlet = dashlet
            break

    if not the_dashlet:
        raise MKUserError("id", _('The dashlet can not be found on the dashboard.'))

    if the_dashlet['type'] not in dashlet_registry:
        raise MKUserError("id", _('The requested dashlet type does not exist.'))

    mtime = html.request.get_integer_input_mandatory('mtime', 0)

    dashlet_instance = None
    try:
        dashlet_type = get_dashlet_type(the_dashlet)
        dashlet_instance = dashlet_type(name, board, ident, the_dashlet)

        dashlet_content_html = _render_dashlet_content(board,
                                                       dashlet_instance,
                                                       is_update=True,
                                                       mtime=mtime)
    except Exception as e:
        if dashlet_instance is None:
            dashlet_instance = _fallback_dashlet_instance(name, board, the_dashlet, ident)
        dashlet_content_html = render_dashlet_exception_content(the_dashlet, ident, e)

    html.write_html(HTML(dashlet_content_html))


def _add_context_to_dashboard(board: DashboardConfig) -> DashboardConfig:
    board = copy.deepcopy(board)
    board.setdefault("single_infos", [])
    board.setdefault("context", {})
    board.setdefault("mandatory_context_filters", [])
    return board


#.
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
    visuals.page_list('dashboards', _("Edit Dashboards"), get_all_dashboards())


#.
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
    visuals.page_create_visual('dashboards', visual_info_registry.keys())


#.
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
    visuals.page_edit_visual('dashboards',
                             get_all_dashboards(),
                             create_handler=create_dashboard,
                             custom_field_handler=custom_field_handler,
                             info_handler=_dashboard_info_handler)


def _dashboard_info_handler(visual):
    # We could use all available infos here, but there is a lot of normally unused stuff. For better
    # usability reduce the list to the (assumed) relevant used ones.
    return ["host", "service"]


def custom_field_handler(dashboard: DashboardConfig) -> None:
    _vs_dashboard().render_input('dashboard', dashboard and dashboard or None)


def create_dashboard(old_dashboard: DashboardConfig, dashboard: DashboardConfig) -> DashboardConfig:
    vs_dashboard = _vs_dashboard()
    board_properties = vs_dashboard.from_html_vars('dashboard')
    vs_dashboard.validate_value(board_properties, 'dashboard')
    dashboard.update(board_properties)

    # Do not remove the dashlet configuration during general property editing
    dashboard['dashlets'] = old_dashboard.get('dashlets', [])
    dashboard['mtime'] = int(time.time())

    return dashboard


def _vs_dashboard() -> Dictionary:
    return Dictionary(
        title=_('Dashboard Properties'),
        render='form',
        optional_keys=False,
        elements=[
            ('show_title',
             Checkbox(
                 title=_('Display dashboard title'),
                 label=_('Show the header of the dashboard with the configured title.'),
                 default_value=True,
             )),
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
                        "the users to first provide some context before rendering the dashboard."),
                )),
        ],
    )


#.
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
    name = html.request.get_str_input_mandatory('name')
    choose_view(name, _('Link existing view'), _create_linked_view_dashlet_spec)


def _create_linked_view_dashlet_spec(dashlet_id: int, view_name: str) -> Dict:
    dashlet = default_dashlet_definition("linked_view")
    dashlet["name"] = view_name
    return dashlet


@cmk.gui.pages.register("create_view_dashlet")
def page_create_view_dashlet() -> None:
    create = html.request.var('create', '1') == '1'
    name = html.request.get_str_input_mandatory('name')

    if create:
        import cmk.gui.views as views  # pylint: disable=import-outside-toplevel
        url = html.makeuri([('back', html.makeuri([]))], filename="create_view_dashlet_infos.py")
        views.show_create_view_dialog(next_url=url)

    else:
        # Choose an existing view from the list of available views
        choose_view(name, _('Copy existing view'), _create_cloned_view_dashlet_spec)


def _create_cloned_view_dashlet_spec(dashlet_id: int, view_name: str) -> Dict:
    dashlet = default_dashlet_definition('view')

    # save the original context and override the context provided by the view
    copy_view_into_dashlet(dashlet, dashlet_id, view_name)
    return dashlet


@cmk.gui.pages.register("create_view_dashlet_infos")
def page_create_view_dashlet_infos() -> None:
    ds_name = html.request.get_str_input_mandatory('datasource')
    if ds_name not in data_source_registry:
        raise MKUserError("datasource", _('The given datasource is not supported'))

    # Create a new view by choosing the datasource and the single object types
    visuals.page_create_visual('views',
                               data_source_registry[ds_name]().infos,
                               next_url=html.makeuri_contextless([
                                   ('name', html.request.var('name')),
                                   ('type', 'view'),
                                   ('datasource', ds_name),
                                   ('back', html.makeuri([])),
                                   ('next',
                                    html.makeuri_contextless([('name', html.request.var('name')),
                                                              ('edit', '1')], 'dashboard.py')),
                               ],
                                                                 filename='edit_dashlet.py'))


def choose_view(name: DashboardName, title: str, create_dashlet_spec_func: Callable) -> None:
    import cmk.gui.views as views  # pylint: disable=import-outside-toplevel
    vs_view = DropdownChoice(
        title=_('View name'),
        choices=views.view_choices,
        sorted=True,
    )

    html.header(title, breadcrumb=visuals.visual_page_breadcrumb("dashboards", title, "edit"))
    html.begin_context_buttons()
    back_url = html.get_url_input(
        "back", "dashboard.py?edit=1&name=%s" % html.urlencode(html.request.var('name')))
    html.context_button(_("Back"), back_url, "back")
    html.end_context_buttons()

    if html.request.var('save') and html.check_transaction():
        try:
            view_name = vs_view.from_html_vars('view')
            vs_view.validate_value(view_name, 'view')

            dashboard = get_permitted_dashboards()[name]
            dashlet_id = len(dashboard['dashlets'])
            dashlet = create_dashlet_spec_func(dashlet_id, view_name)
            add_dashlet(dashlet, dashboard)

            raise HTTPRedirect(
                html.makeuri_contextless(
                    [
                        ("name", name),
                        ("id", str(dashlet_id)),
                        ("back", back_url),
                    ],
                    filename="edit_dashlet.py",
                ))
        except MKUserError as e:
            html.user_error(e)

    html.begin_form('choose_view')
    forms.header(_('Select view'))
    forms.section(vs_view.title())
    vs_view.render_input('view', '')
    html.help(vs_view.help())
    forms.end()

    html.button('save', _('Continue'), 'submit')

    html.hidden_fields()
    html.end_form()
    html.footer()


@cmk.gui.pages.register("edit_dashlet")
def page_edit_dashlet() -> None:
    if not config.user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.request.var('name')
    if not board:
        raise MKUserError("name", _('The name of the dashboard is missing.'))

    ident = html.request.get_integer_input("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _('The requested dashboard does not exist.'))

    if ident is None:
        ty = html.request.get_str_input_mandatory('type')
        mode = 'add'
        title = _('Add Dashlet')

        try:
            dashlet_type = dashlet_registry[ty]
        except KeyError:
            raise MKUserError("type", _('The requested dashlet type does not exist.'))

        # Initial configuration
        dashlet = {
            'position': dashlet_type.initial_position(),
            'size': dashlet_type.initial_size(),
            'single_infos': dashlet_type.single_infos(),
            'type': ty,
        }
        dashlet.update(dashlet_type.default_settings())

        if dashlet_type.has_context():
            dashlet["context"] = {}

        ident = len(dashboard['dashlets'])

        single_infos_raw = html.request.var('single_infos')
        single_infos: List[InfoName] = []
        if single_infos_raw:
            single_infos = single_infos_raw.split(',')
            for key in single_infos:
                if key not in visual_info_registry:
                    raise MKUserError('single_infos', _('The info %s does not exist.') % key)

        if not single_infos:
            single_infos = dashlet_type.single_infos()

        dashlet['single_infos'] = single_infos
    else:
        mode = 'edit'
        title = _('Edit Dashlet')

        try:
            dashlet = dashboard['dashlets'][ident]
        except IndexError:
            raise MKUserError("id", _('The dashlet does not exist.'))

        ty = dashlet['type']
        dashlet_type = dashlet_registry[ty]
        single_infos = dashlet['single_infos']

    html.header(title, breadcrumb=visuals.visual_page_breadcrumb("dashboards", title, mode))

    html.begin_context_buttons()
    back_url = html.get_url_input('back')
    next_url = html.get_url_input('next', back_url)
    html.context_button(_('Back'), back_url, 'back')
    html.context_button(_('All Dashboards'), 'edit_dashboards.py', 'dashboard')
    html.end_context_buttons()

    vs_general = Dictionary(
        title=_('General Settings'),
        render='form',
        optional_keys=['title', 'title_url'],
        elements=[
            ('type', FixedValue(
                ty,
                totext=dashlet_type.title(),
                title=_('Dashlet Type'),
            )),
            visuals.single_infos_spec(single_infos),
            ('background',
             Checkbox(
                 title=_('Colored Background'),
                 label=_('Render background'),
                 help=_('Render gray background color behind the dashlets content.'),
                 default_value=True,
             )),
            ('show_title',
             Checkbox(
                 title=_('Show Title'),
                 label=_('Render the titlebar above the dashlet'),
                 help=_('Render the titlebar including title and link above the dashlet.'),
                 default_value=True,
             )),
            ('title',
             TextUnicode(
                 title=_('Custom Title') + '<sup>*</sup>',
                 help=_(
                     'Most dashlets have a hard coded default title. For example the view snapin '
                     'has even a dynamic title which defaults to the real title of the view. If you '
                     'like to use another title, set it here.'),
                 size=50,
             )),
            ('title_url',
             TextUnicode(
                 title=_('Link of Title'),
                 help=_('The URL of the target page the link of the dashlet should link to.'),
                 size=50,
             )),
        ],
    )

    def dashlet_info_handler(dashlet: DashletConfig) -> List[str]:
        dashlet_type = dashlet_registry[dashlet['type']]
        dashlet_instance = dashlet_type(board, dashboard, ident, dashlet)
        return dashlet_instance.infos()

    context_specs = visuals.get_context_specs(dashlet, info_handler=dashlet_info_handler)

    vs_type: Optional[ValueSpec] = None
    params = dashlet_type.vs_parameters()
    render_input_func = None
    handle_input_func = None
    if isinstance(params, list):
        # TODO: Refactor all params to be a Dictionary() and remove this special case
        vs_type = Dictionary(
            title=_('Properties'),
            render='form',
            optional_keys=dashlet_type.opt_parameters(),
            validate=dashlet_type.validate_parameters_func(),
            elements=params,
        )

    elif isinstance(params, (Dictionary, Transform)):
        vs_type = params

    elif isinstance(params, tuple):
        # It's a tuple of functions which should be used to render and parse the params
        render_input_func, handle_input_func = params

    if html.request.var('save') and html.transaction_valid():
        try:
            general_properties = vs_general.from_html_vars('general')
            vs_general.validate_value(general_properties, 'general')
            dashlet.update(general_properties)
            # Remove unset optional attributes
            if 'title' not in general_properties and 'title' in dashlet:
                del dashlet['title']

            if vs_type:
                type_properties = vs_type.from_html_vars('type')
                vs_type.validate_value(type_properties, 'type')
                dashlet.update(type_properties)

            elif handle_input_func:
                # The returned dashlet must be equal to the parameter! It is not replaced/re-added
                # to the dashboard object. FIXME TODO: Clean this up!
                dashlet = handle_input_func(ident, dashlet)

            if context_specs:
                dashlet['context'] = visuals.process_context_specs(context_specs)

            if mode == "add":
                dashboard['dashlets'].append(dashlet)

            save_all_dashboards()

            html.immediate_browser_redirect(1, next_url)
            if mode == 'edit':
                html.show_message(_('The dashlet has been saved.'))
            else:
                html.show_message(_('The dashlet has been added to the dashboard.'))
            html.reload_sidebar()
            html.footer()
            return

        except MKUserError as e:
            html.user_error(e)

    html.begin_form("dashlet", method="POST")
    vs_general.render_input("general", dashlet)

    if vs_type:
        vs_type.render_input("type", dashlet)
    elif render_input_func:
        render_input_func(dashlet)

    visuals.render_context_specs(dashlet, context_specs)

    forms.end()
    html.show_localization_hint()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

    html.footer()


@cmk.gui.pages.register("clone_dashlet")
def page_clone_dashlet() -> None:
    if not config.user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.request.var('name')
    if not board:
        raise MKUserError("name", _('The name of the dashboard is missing.'))

    ident = html.request.get_integer_input_mandatory("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _('The requested dashboard does not exist.'))

    try:
        dashlet_spec = dashboard['dashlets'][ident]
    except IndexError:
        raise MKUserError("id", _('The dashlet does not exist.'))

    new_dashlet_spec = dashlet_spec.copy()
    dashlet_type = get_dashlet_type(new_dashlet_spec)
    new_dashlet_spec["position"] = dashlet_type.initial_position()

    dashboard['dashlets'].append(new_dashlet_spec)
    dashboard['mtime'] = int(time.time())
    save_all_dashboards()

    raise HTTPRedirect(html.get_url_input('back'))


@cmk.gui.pages.register("delete_dashlet")
def page_delete_dashlet() -> None:
    if not config.user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.request.var('name')
    if not board:
        raise MKUserError("name", _('The name of the dashboard is missing.'))

    ident = html.request.get_integer_input_mandatory("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _('The requested dashboard does not exist.'))

    try:
        _dashlet = dashboard['dashlets'][ident]  # noqa: F841
    except IndexError:
        raise MKUserError("id", _('The dashlet does not exist.'))

    dashboard['dashlets'].pop(ident)
    dashboard['mtime'] = int(time.time())
    save_all_dashboards()

    raise HTTPRedirect(html.get_url_input('back'))


#.
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
    if not config.user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = html.request.get_str_input_mandatory('name')
    ident = html.request.get_integer_input_mandatory("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _('The requested dashboard does not exist.'))

    try:
        dashlet = dashboard['dashlets'][ident]
    except IndexError:
        raise MKUserError("id", _('The dashlet does not exist.'))

    return dashlet, dashboard


@cmk.gui.pages.register("ajax_dashlet_pos")
def ajax_dashlet_pos() -> None:
    dashlet, board = check_ajax_update()

    board['mtime'] = int(time.time())

    dashlet['position'] = (html.request.get_integer_input_mandatory("x"),
                           html.request.get_integer_input_mandatory("y"))
    dashlet['size'] = (html.request.get_integer_input_mandatory("w"),
                       html.request.get_integer_input_mandatory("h"))
    save_all_dashboards()
    html.write('OK %d' % board['mtime'])


@cmk.gui.pages.register("ajax_delete_user_notification")
def ajax_delete_user_notification() -> None:
    msg_id = html.request.get_str_input_mandatory("id")
    notify.delete_gui_message(msg_id)


#.
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
        'type': ty,
        'position': dashlet_registry[ty].initial_position(),
        'size': dashlet_registry[ty].initial_size(),
        'show_title': True,
    }


def add_dashlet(dashlet: DashletConfig, dashboard: DashboardConfig) -> None:
    dashboard['dashlets'].append(dashlet)
    dashboard['mtime'] = int(time.time())
    save_all_dashboards()
