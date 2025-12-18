#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

"""HTML page handler for generating the (a) dashboard. The name
of the dashboard to render is given in the HTML variable 'name'.
"""

import copy
from collections.abc import Iterable
from dataclasses import asdict
from typing import Literal

import cmk.ccc.version as cmk_version
from cmk.ccc.exceptions import MKException, MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui import crash_handler, visuals
from cmk.gui.config import Config
from cmk.gui.crash_handler import GUIDetails
from cmk.gui.exceptions import MKAuthException, MKMissingDataError, MKUserError
from cmk.gui.graphing import MKCombinedGraphLimitExceededError
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenuLink,
)
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import VisualContext, VisualTypeName
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.views.page_ajax_filters import ABCAjaxInitialFilters
from cmk.gui.visuals import visual_page_breadcrumb
from cmk.gui.visuals._filter_context import requested_context_from_request
from cmk.gui.visuals.info import visual_info_registry
from cmk.utils import paths

from ._network_topology import get_topology_context_and_filters
from .breadcrumb import dashboard_breadcrumb, EvaluatedBreadcrumbItem
from .dashlet import (
    Dashlet,
    dashlet_registry,
    DashletConfig,
    StaticTextDashlet,
    StaticTextDashletConfig,
)
from .metadata import DashboardMetadataObject
from .page_edit_dashboards import PAGE_EDIT_DASHBOARDS_LINK
from .store import (
    get_permitted_dashboards,
    get_permitted_dashboards_by_owners,
    load_dashboard,
)
from .type_defs import DashboardConfig, DashboardName

__all__ = ["ajax_dashlet", "AjaxInitialDashboardFilters"]


def page_dashboard_app(ctx: PageContext) -> None:
    mode: Literal["display", "create", "clone", "settings"] = (
        "display"  # edit mode lives within the page
    )

    if ctx.request.var("mode") == "create":
        if not user.may("general.edit_dashboards"):
            raise MKAuthException(_("You are not allowed to create dashboards."))
        mode = "create"

    elif ctx.request.var("mode") == "edit_settings":
        if not user.may("general.edit_dashboards"):
            raise MKAuthException(_("You are not allowed to edit dashboards."))
        mode = "settings"

    elif ctx.request.var("mode") == "clone":
        if not user.may("general.edit_dashboards"):
            raise MKAuthException(_("You are not allowed to clone dashboards."))
        mode = "clone"

    name = ctx.request.get_ascii_input_mandatory("name", "")

    if not name:
        name = _get_default_dashboard_name()
        ctx.request.set_var("name", name)  # TODO: this must be done on the frontend side

    loaded_dashboard_properties = None
    if mode in {"display", "settings", "clone"}:
        permitted_dashboards = get_permitted_dashboards()
        board = load_dashboard(permitted_dashboards, name)
        requested_context = requested_context_from_request(["host", "service"])

        board_context = visuals.active_context_from_request(["host", "service"], board["context"])
        board["context"] = board_context
        title = visuals.visual_title("dashboard", board, board_context)
        user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
        # some dashboards have more complicated context requirements when loaded, these are
        # constructed when clicking on a linking dashboard which means that this will (for now
        # with the current architecture) always go through a full page reload rather than a
        # state changing action. Hence, we can rely on the breadcrumb building mechanism here
        # Loading a dashboard on the frontend through other means will only necessitate the
        # simple breadcrumb as it does not have any prior context
        breadcrumb = dashboard_breadcrumb(name, board, title, board_context, user_permissions)

        loaded_dashboard_properties = {
            "name": name,
            "metadata": asdict(
                DashboardMetadataObject.from_dashboard_config(board, user_permissions)
            ),
            "filter_context": {
                "context": requested_context,
                # determines if the requested filters should overwrite the dashboard filters or
                # merge them with dashboard filters
                "application_mode": "overwrite" if ctx.request.has_var("active_") else "merge",
            },
        }
    else:
        visual_name: VisualTypeName = "dashboards"
        title = _("Create dashboard")
        breadcrumb = visual_page_breadcrumb(visual_name, title, "create")

    html.body_start()
    html.begin_page_content(enable_scrollbar=True)

    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.COMMUNITY:
        available_layouts = ["relative_grid"]
        available_features = "restricted"

    else:
        available_layouts = ["relative_grid", "responsive_grid"]
        available_features = "unrestricted"

    page_properties = {
        "initial_breadcrumb": [
            asdict(EvaluatedBreadcrumbItem.from_breadcrumb_item(item)) for item in breadcrumb
        ],
        # TODO: consider adding initial title as well due to context generation
        "dashboard": loaded_dashboard_properties,
        "mode": mode,
        # required for edit, clone and new dashboard creation
        "can_edit_dashboards": user.may("general.edit_dashboards"),
        "url_params": {"ifid": ctx.request.get_ascii_input("ifid")},
        "links": {
            "list_dashboards": f"{PAGE_EDIT_DASHBOARDS_LINK}.py",
            "user_guide": "https://docs.checkmk.com/master/en/dashboards.html",
            "navigation_embedding_page": makeuri_contextless(ctx.request, [], filename="index.py"),
        },
        "available_layouts": available_layouts,
        "available_features": available_features,
    }

    html.vue_component("cmk-dashboard", data=page_properties)


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
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.COMMUNITY:
        return "main"  # problems = main in community edition
    return "main" if user.may("general.see_all") and user.may("dashboard.main") else "problems"


def _render_dashlet(
    config: Config,
    user_permissions: UserPermissions,
    board: DashboardConfig,
    dashlet: Dashlet,
    is_update: bool,
    mtime: int,
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
        content = _render_dashlet_content(
            config, user_permissions, board, dashlet, is_update=is_update, mtime=board["mtime"]
        )

    except Exception as e:
        content = render_dashlet_exception_content(dashlet, e)

    return title, content


def _render_dashlet_content(
    config: Config,
    user_permissions: UserPermissions,
    board: DashboardConfig,
    dashlet: Dashlet,
    is_update: bool,
    mtime: int,
) -> HTML:
    with output_funnel.plugged():
        if is_update:
            dashlet.update(config, user_permissions)
        else:
            dashlet.show(config)

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

    # I added MKGeneralException during a refactoring, but I did not check if it is needed.
    if isinstance(e, MKException | MKGeneralException):
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


def _minimal_context(
    mandatory_filters: Iterable[str], known_context: VisualContext
) -> VisualContext:
    filter_context: VisualContext = {name: {} for name in mandatory_filters}
    return visuals.get_merged_context(filter_context, known_context)


class AjaxInitialDashboardFilters(ABCAjaxInitialFilters):
    def get_context(self, page_name: str) -> VisualContext:
        return self._get_context(page_name)

    def _get_context(self, page_name: str) -> VisualContext:
        dashboard_name = page_name
        board = load_dashboard(
            get_permitted_dashboards(),
            dashboard_name,
        )

        # For the topology dashboard filters are retrieved from a corresponding view context.
        # This should not be needed here. Can't we load the context from the board as we usually do?
        if page_name == "topology":
            _context, show_filters = get_topology_context_and_filters()
            return {
                f.ident: board["context"].get(f.ident, {}) for f in show_filters if f.available()
            }

        return _minimal_context(_get_mandatory_filters(board, set()), board["context"])


def _dashboard_add_dashlet_back_http_var(request: Request) -> tuple[str, str]:
    return "back", makeuri(request, [("edit", "1")])


def _dashboard_add_view_dashlet_link(
    request: Request,
    owner: UserId,
    name: DashboardName,
    create: Literal["0", "1"],
    filename: str,
) -> PageMenuLink:
    return make_simple_link(
        makeuri_contextless(
            request,
            [
                ("owner", owner),
                ("name", name),
                ("create", create),
                _dashboard_add_dashlet_back_http_var(request),
            ],
            filename=filename,
        )
    )


def _dashboard_add_non_view_dashlet_link(
    request: Request,
    owner: UserId,
    name: DashboardName,
    dashlet_type: str,
) -> PageMenuLink:
    return make_simple_link(
        makeuri_contextless(
            request,
            [
                ("owner", owner),
                ("name", name),
                ("create", "0"),
                _dashboard_add_dashlet_back_http_var(request),
                ("type", dashlet_type),
            ],
            filename="edit_dashlet.py",
        )
    )


def get_dashlet_type(dashlet_spec: DashletConfig) -> type[Dashlet]:
    return dashlet_registry[dashlet_spec["type"]]


def ajax_dashlet(ctx: PageContext) -> None:
    """Render the inner HTML of a dashlet"""
    name = request.get_ascii_input_mandatory("name", "")
    if not name:
        raise MKUserError("name", _("The name of the dashboard is missing."))

    owner = request.get_validated_type_input_mandatory(UserId, "owner")
    try:
        board = get_permitted_dashboards_by_owners()[name][owner]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    board = copy.deepcopy(board)
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

    # TODO: temporary solution to enable embedded_view for old view dashlet
    embedded_views = board.get("embedded_views", {})
    if dashlet_spec["type"] == "embedded_view":
        reference_view = dashlet_spec["name"]  # type: ignore[typeddict-item]
        assert isinstance(reference_view, str)
        dashlet_spec = {  # type: ignore[typeddict-unknown-key]
            **dashlet_spec,
            **embedded_views[reference_view],
            "type": "view",
            # the following are required but have no influence since it's an iframe context
            "sort_index": 100,
            "is_show_more": False,
            "add_context_to_title": False,
        }

    dashlet = None
    try:
        dashlet_type = get_dashlet_type(dashlet_spec)
        dashlet = dashlet_type(name, owner, board, ident, dashlet_spec)
        _title, content = _render_dashlet(
            ctx.config,
            UserPermissions.from_config(ctx.config, permission_registry),
            board,
            dashlet,
            is_update=True,
            mtime=mtime,
        )
    except Exception as e:
        if dashlet is None:
            dashlet = _fallback_dashlet(name, owner, board, dashlet_spec, ident)
        content = render_dashlet_exception_content(dashlet, e)

    html.write_html(HTML.with_escaping(content))
