#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""HTML page handler for generating the (a) dashboard. The name
of the dashboard to render is given in the HTML variable 'name'.
"""

import copy
import json
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Literal

import cmk.ccc.version as cmk_version
from cmk.ccc.exceptions import MKException
from cmk.ccc.user import UserId

from cmk.utils import paths

from cmk.gui import crash_handler, visuals
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.crash_handler import GUIDetails
from cmk.gui.exceptions import MKAuthException, MKMissingDataError, MKUserError
from cmk.gui.graphing._utils import MKCombinedGraphLimitExceededError
from cmk.gui.hooks import call as call_hooks
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    make_javascript_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuEntryCEEOnly,
    PageMenuLink,
    PageMenuSidePopup,
    PageMenuTopic,
)
from cmk.gui.type_defs import InfoName, VisualContext
from cmk.gui.utils.filter import check_if_non_default_filter_in_request
from cmk.gui.utils.html import HTML
from cmk.gui.utils.ntop import is_ntop_configured
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.views.page_ajax_filters import ABCAjaxInitialFilters
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.watolib.activate_changes import get_pending_changes_tooltip, has_pending_changes
from cmk.gui.watolib.users import get_enabled_remote_sites_for_logged_in_user

from ._network_topology import get_topology_context_and_filters
from .breadcrumb import dashboard_breadcrumb
from .builtin_dashboards import GROW, MAX
from .dashlet import (
    ABCFigureDashlet,
    Dashlet,
    dashlet_registry,
    DashletConfig,
    DashletId,
    DashletRefreshAction,
    DashletRefreshInterval,
    StaticTextDashlet,
    StaticTextDashletConfig,
)
from .store import (
    get_all_dashboards,
    get_permitted_dashboards,
    get_permitted_dashboards_by_owners,
    load_dashboard,
    save_all_dashboards,
    save_and_replicate_all_dashboards,
)
from .type_defs import DashboardConfig, DashboardName

__all__ = ["page_dashboard", "ajax_dashlet", "AjaxInitialDashboardFilters"]

DASHLET_PADDING = (
    26,
    4,
    4,
    4,
    4,
)  # Margin (N, E, S, W, N w/o title) between outer border of dashlet and its content
RASTER = 10  # Raster the dashlet coords are measured in (px)


def page_dashboard(config: Config) -> None:
    name = request.get_ascii_input_mandatory("name", "")
    if not name:
        name = _get_default_dashboard_name()
        request.set_var("name", name)  # make sure that URL context is always complete

    draw_dashboard(name)


def _get_default_dashboard_name() -> str:
    """Return the default dashboard name for the current site

    We separate our users into two groups:

    1. Those WITH the permission "see all hosts / service". Which are mainly administrative users.

    These are starting with the main overview dashboard which either shows a site drill down snap-in
    (in case multiple sites are configured) or the hosts of their site (in case there is only a
    single site configured).

    2. Those WITHOUT the permission "see all hosts / service". Which are normal users.

    They will see the dashboard that has been built for operators and is built to show only the host
    and service problems that are relevant for the user.
    """
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CRE:
        return "main"  # problems = main in raw edition
    return "main" if user.may("general.see_all") and user.may("dashboard.main") else "problems"


# Actual rendering function
def draw_dashboard(name: DashboardName) -> None:
    mode = "display"
    if request.var("edit") == "1":
        mode = "edit"

    if mode == "edit" and not user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    need_replication = False
    permitted_dashboards = get_permitted_dashboards()
    board = load_dashboard(permitted_dashboards, name)

    owner = board["owner"]
    if mode == "edit" and owner == UserId.builtin():
        # Trying to edit a built-in dashboard results in doing a copy
        all_dashboards = get_all_dashboards()
        active_user = user.id
        assert active_user is not None
        board = copy.deepcopy(board)
        board["owner"] = active_user
        board["public"] = False

        all_dashboards[(active_user, name)] = board
        permitted_dashboards[name] = board
        save_all_dashboards()
        need_replication = True

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

    dashlets = _get_dashlets(name, owner, board)

    missing_single_infos: set[InfoName] = set()
    unconfigured_single_infos: set[InfoName] = set()
    for dashlet in dashlets:
        missing_single_infos.update(dashlet.missing_single_infos())
        unconfigured_single_infos.update(dashlet.unconfigured_single_infos())

    html.add_body_css_class("dashboard")
    breadcrumb = dashboard_breadcrumb(name, board, title, board_context)
    make_header(
        html,
        title,
        breadcrumb=breadcrumb,
        page_menu=_page_menu(
            breadcrumb, name, board, board_context, unconfigured_single_infos, mode
        ),
    )

    # replication is only needed if we have remote sites
    if need_replication and get_enabled_remote_sites_for_logged_in_user(user):
        save_and_replicate_all_dashboards(
            makeuri(request, [("name", name), ("edit", "1" if mode == "edit" else "0")])
        )

    call_hooks("rmk_dashboard_banner", name)

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
        "grid_size": RASTER,
        "dashlet_padding": DASHLET_PADDING,
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


def _get_dashlets(name: DashboardName, owner: UserId, board: DashboardConfig) -> list[Dashlet]:
    """Return dashlet instances of the dashboard"""
    dashlets: list[Dashlet] = []
    for nr, dashlet_spec in enumerate(board["dashlets"]):
        try:
            dashlet_type = get_dashlet_type(dashlet_spec)
            dashlet = dashlet_type(name, owner, board, nr, dashlet_spec)
        except KeyError as e:
            info_text = (
                _(
                    "Dashlet type %s could not be found. "
                    "Please remove it from your dashboard configuration."
                )
                % e
            )
            dashlet = _fallback_dashlet(name, owner, board, dashlet_spec, nr, info_text=info_text)
        except Exception:
            dashlet = _fallback_dashlet(name, owner, board, dashlet_spec, nr)

        dashlets.append(dashlet)

    return dashlets


def _get_refresh_dashlets(
    dashlets: list[Dashlet],
) -> list[tuple[DashletId, DashletRefreshInterval, DashletRefreshAction]]:
    """Return information for dashlets with automatic refresh"""
    refresh_dashlets = []
    for dashlet in dashlets:
        refresh = get_dashlet_refresh(dashlet)
        if refresh:
            refresh_dashlets.append(refresh)
    return refresh_dashlets


def _get_resize_dashlets(dashlets: list[Dashlet]) -> dict[DashletId, str]:
    """Get list of javascript functions to execute after resizing the dashlets"""
    on_resize_dashlets: dict[DashletId, str] = {}
    for dashlet in dashlets:
        on_resize = get_dashlet_on_resize(dashlet)
        if on_resize:
            on_resize_dashlets[dashlet.dashlet_id] = on_resize
    return on_resize_dashlets


def _get_dashlet_coords(dashlets: list[Dashlet]) -> list[dict[str, int]]:
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
) -> tuple[HTML | str, HTML | str]:
    content: HTML | str = ""
    title: HTML | str = ""
    missing_infos = visuals.missing_context_filters(
        set(board["mandatory_context_filters"]), board["context"]
    )
    missing_infos.update(dashlet.missing_single_infos())
    try:
        if missing_infos:
            return (
                _("Filter context missing"),
                html.render_warning(
                    _(
                        "Unable to render this element, "
                        "because we miss some required context information (%s). Please update the "
                        "form on the right to make this element render."
                    )
                    % ", ".join(sorted(missing_infos))
                ),
            )

        title = dashlet.render_title_html()
        content = _render_dashlet_content(board, dashlet, is_update=is_update, mtime=board["mtime"])

    except Exception as e:
        content = render_dashlet_exception_content(dashlet, e)

    return title, content


def _render_dashlet_content(
    board: DashboardConfig, dashlet: Dashlet, is_update: bool, mtime: int
) -> HTML:
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

        return HTML.without_escaping(output_funnel.drain())


def render_dashlet_exception_content(dashlet: Dashlet, e: Exception) -> HTML | str:
    if isinstance(e, MKMissingDataError | MKCombinedGraphLimitExceededError):
        return html.render_message(str(e))

    if not isinstance(e, MKUserError):
        # Do not write regular error messages related to normal user interaction and validation to
        # the web.log
        logger.exception(
            "Problem while rendering dashboard element %d of type %s",
            dashlet.dashlet_id,
            dashlet.type_name(),
        )

    if isinstance(e, MKException):
        return html.render_error(
            _(
                "Problem while rendering dashboard element %d of type %s: %s. Have a look at "
                "<tt>var/log/web.log</tt> for further information."
            )
            % (dashlet.dashlet_id, dashlet.type_name(), str(e))
        )

    with output_funnel.plugged():
        crash_handler.handle_exception_as_gui_crash_report(
            details=GUIDetails(
                dashlet_id=dashlet.dashlet_id,
                dashlet_type=dashlet.type_name(),
                dashlet_spec=dashlet.dashlet_spec,
                page="unknown",
                vars={},
                username=None,
                user_agent="unknown",
                referer="unknown",
                is_mobile=False,
                is_ssl_request=False,
                language="unknown",
                request_method="unknown",
            )
        )
        return output_funnel.drain()


def _fallback_dashlet(
    name: DashboardName,
    owner: UserId,
    board: DashboardConfig,
    dashlet_spec: DashletConfig,
    dashlet_id: int,
    info_text: str = "",
) -> StaticTextDashlet:
    """Create some place holder dashlet to show in case the original dashlet could not be
    initialized"""
    return StaticTextDashlet(
        name,
        owner,
        board,
        dashlet_id,
        StaticTextDashletConfig(
            {
                "type": "nodata",
                "text": info_text,
                "position": dashlet_spec["position"],
                "size": dashlet_spec["size"],
            }
        ),
    )


def _get_mandatory_filters(
    board: DashboardConfig, unconfigured_single_infos: set[str]
) -> Iterable[str]:
    # Get required single info keys (the ones that are not set by the config)
    for info_key in unconfigured_single_infos:
        for info, _unused in visual_info_registry[info_key]().single_spec:
            yield info

    # Get required context filters set in the dashboard config
    yield from board["mandatory_context_filters"]


def _page_menu(
    breadcrumb: Breadcrumb,
    name: DashboardName,
    board: DashboardConfig,
    board_context: VisualContext,
    unconfigured_single_infos: set[str],
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
        has_pending_changes=has_pending_changes(),
        pending_changes_tooltip=get_pending_changes_tooltip(),
        # Disable suggestion rendering because it makes the page content shift downwards, which is
        # unwanted on unscrollable dashboards
        enable_suggestions=False,
    )

    _extend_display_dropdown(name, menu, board, board_context, unconfigured_single_infos)

    return menu


def _page_menu_dashboards(name: DashboardName) -> Iterable[PageMenuTopic]:
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CRE:
        linked_dashboards = ["main", "checkmk"]  # problems = main in raw edition
    else:
        linked_dashboards = ["main", "problems", "checkmk"]

    yield PageMenuTopic(
        title=_("Related dashboards"),
        entries=list(_dashboard_related_entries(name, linked_dashboards)),
    )
    yield PageMenuTopic(
        title=_("Other dashboards"),
        entries=list(_dashboard_other_entries(name, linked_dashboards)),
    )
    yield PageMenuTopic(
        title=_("Customize"),
        entries=(
            [
                PageMenuEntry(
                    title=_("Edit dashboards"),
                    icon_name="dashboard",
                    item=make_simple_link("edit_dashboards.py"),
                )
            ]
            if user.may("general.edit_dashboards")
            else []
        ),
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
        title=_("HW/SW Inventory"),
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

    if board["owner"] == UserId.builtin():
        # Not owned dashboards must be cloned before being able to edit. Do not switch to
        # edit mode using javascript, use the URL with edit=1. When this URL is opened,
        # the dashboard will be cloned for this user
        yield PageMenuEntry(
            title=_("Clone built-in dashboard"),
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
            f'cmk.dashboard.toggle_dashboard_edit("{edit_text}", "{display_text}")'
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
                    ("mode", "edit"),
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
    for dashboard_name, dashboard in sorted(
        get_permitted_dashboards().items(), key=lambda x: x[1]["sort_index"]
    ):
        if name in linked_dashboards and dashboard_name in linked_dashboards:
            continue
        if dashboard["hidden"]:
            continue
        if ntop_not_configured and dashboard_name.startswith("ntop_"):
            continue

        yield PageMenuEntry(
            title=str(dashboard["title"]),
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
            title=str(dashboard["title"]),
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
    name: str,
    menu: PageMenu,
    board: DashboardConfig,
    board_context: VisualContext,
    unconfigured_single_infos: set[str],
) -> None:
    display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())

    minimal_context = _minimal_context(
        _get_mandatory_filters(board, unconfigured_single_infos), board_context
    )
    # Like _dashboard_info_handler we assume that only host / service filters are relevant
    info_list = ["host", "service"]

    is_filter_set = check_if_non_default_filter_in_request(
        AjaxInitialDashboardFilters().get_context(page_name=name)
    )

    display_dropdown.topics.insert(
        0,
        PageMenuTopic(
            title=_("Filter"),
            entries=[
                PageMenuEntry(
                    title=_("Filter"),
                    icon_name=(
                        {"icon": "filter", "emblem": "warning"} if is_filter_set else "filter"
                    ),
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


class AjaxInitialDashboardFilters(ABCAjaxInitialFilters):
    def get_context(self, page_name: str) -> VisualContext:
        return self._get_context(page_name)

    def _get_context(self, page_name: str) -> VisualContext:
        dashboard_name = page_name
        board = load_dashboard(
            get_permitted_dashboards(),
            dashboard_name,
        )
        board = _add_context_to_dashboard(board)

        # For the topology dashboard filters are retrieved from a corresponding view context.
        # This should not be needed here. Can't we load the context from the board as we usually do?
        if page_name == "topology":
            _context, show_filters = get_topology_context_and_filters()
            return {
                f.ident: board["context"].get(f.ident, {}) for f in show_filters if f.available()
            }

        return _minimal_context(_get_mandatory_filters(board, set()), board["context"])


def _dashboard_add_dashlet_back_http_var() -> tuple[str, str]:
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


def _dashboard_add_views_dashlet_entries(
    name: DashboardName,
) -> Iterable[PageMenuEntry]:
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


def _dashboard_add_graphs_dashlet_entries(
    name: DashboardName,
) -> Iterable[PageMenuEntry]:
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


def _dashboard_add_state_dashlet_entries(
    name: DashboardName,
) -> Iterable[PageMenuEntryCEEOnly]:
    yield PageMenuEntryCEEOnly(
        title="Host state",
        icon_name="host_state",
        item=_dashboard_add_non_view_dashlet_link(name, "state_host"),
    )

    yield PageMenuEntryCEEOnly(
        title="Service state",
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


def _dashboard_add_inventory_dashlet_entries(
    name: DashboardName,
) -> Iterable[PageMenuEntryCEEOnly]:
    yield PageMenuEntryCEEOnly(
        title="HW/SW Inventory of host",
        icon_name="inventory",
        item=_dashboard_add_non_view_dashlet_link(name, "inventory"),
    )


def _dashboard_add_metrics_dashlet_entries(
    name: DashboardName,
) -> Iterable[PageMenuEntryCEEOnly]:
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

    yield PageMenuEntryCEEOnly(
        title="Top list",
        icon_name="rank",
        item=_dashboard_add_non_view_dashlet_link(name, "top_list"),
    )


def _dashboard_add_checkmk_dashlet_entries(
    name: DashboardName,
) -> Iterable[PageMenuEntry]:
    yield PageMenuEntryCEEOnly(
        title="Site overview",
        icon_name="site_overview",
        item=_dashboard_add_non_view_dashlet_link(name, "site_overview"),
    )

    yield PageMenuEntryCEEOnly(
        title="Alert overview",
        icon_name={"icon": "alerts", "emblem": "statistic"},
        item=_dashboard_add_non_view_dashlet_link(name, "alert_overview"),
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
    )


def _dashboard_add_ntop_dashlet_entries(
    name: DashboardName,
) -> Iterable[PageMenuEntryCEEOnly]:
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


def _dashboard_add_other_dashlet_entries(
    name: DashboardName,
) -> Iterable[PageMenuEntry]:
    yield PageMenuEntry(
        title="Custom URL",
        icon_name="dashlet_url",
        item=_dashboard_add_non_view_dashlet_link(name, "url"),
    )

    yield PageMenuEntry(
        title="Static text",
        icon_name="dashlet_nodata",
        item=_dashboard_add_non_view_dashlet_link(name, "nodata"),
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


# Dashlets using static content (such as an iframe) will not be
# refreshed by us but need to do that themselves.
# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_refresh(
    dashlet: Dashlet,
) -> tuple[DashletId, DashletRefreshInterval, DashletRefreshAction] | None:
    if (
        not dashlet.is_iframe_dashlet()
        and (refresh := dashlet.refresh_interval())
        and (action := dashlet.get_refresh_action())
    ):
        return (dashlet.dashlet_id, refresh, action)
    return None


# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_on_resize(dashlet: Dashlet) -> str | None:
    on_resize = dashlet.on_resize()
    if on_resize:
        return "(function() {%s})" % on_resize
    return None


# TODO: Refactor this to Dashlet or later Dashboard class
def get_dashlet_dimensions(dashlet: Dashlet) -> dict[str, int]:
    dimensions = {}
    dimensions["x"], dimensions["y"] = dashlet.position()
    dimensions["w"], dimensions["h"] = dashlet.size()
    return dimensions


def get_dashlet_type(dashlet_spec: DashletConfig) -> type[Dashlet]:
    return dashlet_registry[dashlet_spec["type"]]


def draw_dashlet(dashlet: Dashlet, content: HTML | str, title: HTML | str) -> None:
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
    html.write_html(HTML.with_escaping(content))
    html.close_div()


def ajax_dashlet(config: Config) -> None:
    """Render the inner HTML of a dashlet"""
    name = request.get_ascii_input_mandatory("name", "")
    if not name:
        raise MKUserError("name", _("The name of the dashboard is missing."))

    owner = request.get_validated_type_input_mandatory(UserId, "owner")
    try:
        board = get_permitted_dashboards_by_owners()[name][owner]
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
        dashlet = dashlet_type(name, owner, board, ident, dashlet_spec)
        _title, content = _render_dashlet(board, dashlet, is_update=True, mtime=mtime)
    except Exception as e:
        if dashlet is None:
            dashlet = _fallback_dashlet(name, owner, board, dashlet_spec, ident)
        content = render_dashlet_exception_content(dashlet, e)

    html.write_html(HTML.with_escaping(content))


# TODO: This should not be done during runtime at "random" places. Instead the typing and
# cmk.update_config need to ensure that the data is correct. However, there is the chance that this
# has already been done in the meantime.
def _add_context_to_dashboard(board: DashboardConfig) -> DashboardConfig:
    board = copy.deepcopy(board)
    board.setdefault("single_infos", [])
    board.setdefault("context", {})
    board.setdefault("mandatory_context_filters", [])
    return board
