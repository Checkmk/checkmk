#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

import json
import uuid
from collections.abc import Iterator
from typing import cast, override

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui.graphing import (
    GraphSpecification,
    parse_raw_graph_specification,
    TemplateGraphSpecification,
)
from cmk.gui.http import Request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_javascript_link, PageMenuEntry
from cmk.gui.type_defs import DashboardEmbeddedViewSpec, IconNames, StaticIcon, VisualContext
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.visuals.type import VisualType

from .dashlet import (
    copy_view_into_dashlet,
    dashlet_registry,
    DashletConfig,
)
from .metadata import dashboard_uses_relative_grid
from .store import (
    add_dashlet,
    get_all_dashboards,
    get_permitted_dashboards,
    load_dashboard,
)
from .type_defs import (
    ABCGraphDashletConfig,
    DashboardConfig,
    DashboardName,
    EmbeddedViewDashletConfig,
    ViewDashletConfig,
)


class VisualTypeDashboards(VisualType):
    @property
    @override
    def ident(self) -> str:
        return "dashboards"

    @property
    @override
    def title(self) -> str:
        return _("dashboard")

    @property
    @override
    def plural_title(self) -> str:
        return _("dashboards")

    @property
    @override
    def ident_attr(self) -> str:
        return "name"

    @property
    @override
    def multicontext_links(self) -> bool:
        return False

    @property
    @override
    def show_url(self) -> str:
        return "dashboard.py"

    @override
    def page_menu_add_to_entries(
        self, add_type: str, user_permissions: UserPermissions
    ) -> Iterator[PageMenuEntry]:
        if not user.may("general.edit_dashboards"):
            return

        if add_type in ["availability", "graph_collection"]:
            return

        for name, board in get_permitted_dashboards().items():
            yield PageMenuEntry(
                title=str(board["title"]),
                icon_name=StaticIcon(IconNames.dashboard),
                item=make_javascript_link(
                    "cmk.popup_menu.add_to_visual('dashboards', %s)" % json.dumps(name)
                ),
            )

    @override
    def add_visual_handler(
        self,
        request: Request,
        target_visual_name: str,
        add_type: str,
        context: VisualContext | None,
        parameters: dict,
        user_permissions: UserPermissions,
    ) -> None:
        # TODO: this function really warrants some refactoring, there are more comments than code
        #  at this point (the used bits are the ones which should be refactored though)
        if not user.may("general.edit_dashboards"):
            # Exceptions do not work here.
            return

        if add_type == "pnpgraph" and context is None:
            # Checkmk Community graphs are added correctly by htdocs/js/checkmk.js create_pnp_graph().
            # Commercial editions graphs:
            #
            # Context will always be None here, but the specification (in parameters)
            # will contain it. Transform the data to the format needed by the dashlets.
            #
            # Example:
            # parameters = [ 'template', {'service_description': 'CPU load', 'site': 'mysite',
            #                         'graph_index': 0, 'host_name': 'server123'}])
            add_type, context, parameters = self._handle_add_graph(
                parse_raw_graph_specification(parameters["definition"]["specification"])
            )

        # the DashletConfig below doesn't take None for context, so at this point we should have one
        if context is None:
            raise ValueError(
                "'context' should have been provided or this should have been a 'pnpgraph'"
            )

        permitted_dashboards = get_permitted_dashboards()
        dashboard = load_dashboard(permitted_dashboards, target_visual_name)

        dashlet_spec: DashletConfig = {
            "type": add_type,
            "show_title": True,
        }

        self._update_dashlet_spec(dashlet_spec, dashboard, add_type)

        dashlet_spec["context"] = context
        if add_type == "view":
            view_name = parameters["name"]
            dashlet_spec = cast(ViewDashletConfig, dashlet_spec)
            copy_view_into_dashlet(
                request,
                dashlet_spec,
                len(dashboard["dashlets"]),
                view_name,
                add_context=context,
            )

            view_spec, embedded_view_dashlet = self._create_embedded_view_spec_and_dashlet(
                dashlet_spec
            )
            dashboard.setdefault("embedded_views", {})[embedded_view_dashlet["name"]] = view_spec
            add_dashlet(embedded_view_dashlet, dashboard)
            # Directly go to the dashboard in edit mode. We send the URL as an answer
            # to the AJAX request
            response.set_data("OK dashboard.py?name=" + target_visual_name + "&mode=edit_layout")
            return None

        # We don't know if what we get as parameters actually fits a DashletConfig.
        dashlet_spec.update(parameters)  # type: ignore[typeddict-item]
        if add_type in ["pnpgraph", "custom_graph"]:
            dashlet_spec = cast(ABCGraphDashletConfig, dashlet_spec)

            # The "add to visual" popup does not provide a timerange information,
            # but this is not an optional value. Set it to 25h initially.
            dashlet_spec.setdefault("timerange", "25h")

        add_dashlet(dashlet_spec, dashboard)

        # Directly go to the dashboard in edit mode. We send the URL as an answer
        # to the AJAX request
        response.set_data("OK dashboard.py?name=" + target_visual_name + "&mode=edit_layout")

    @override
    def visuals(self) -> dict[tuple[UserId, DashboardName], DashboardConfig]:
        return get_all_dashboards()

    @override
    def permitted_visuals(
        self,
        visuals: dict[tuple[UserId, DashboardName], DashboardConfig],
        user_permissions: UserPermissions,
    ) -> dict[DashboardName, DashboardConfig]:
        return get_permitted_dashboards()

    def _handle_add_graph(
        self,
        graph_specification: GraphSpecification,
    ) -> tuple[str, VisualContext, dict[str, object]]:
        if isinstance(graph_specification, TemplateGraphSpecification):
            return (
                "pnpgraph",
                {
                    "host": {"host": graph_specification.host_name},
                    # The service context has to be set, even for host graphs. Otherwise the
                    # pnpgraph dashlet would complain about missing context information when
                    # displaying host graphs.
                    "service": {"service": graph_specification.service_description},
                },
                {
                    "source": graph_specification.graph_id,
                    "single_infos": [],
                },
            )

        raise MKGeneralException(
            _("Graph specification '%s' is insufficient for dashboard.")
            % graph_specification.graph_type
        )

    @staticmethod
    def _add_relative_grid_layout_to_dashlet_spec(
        dashlet_spec: DashletConfig,
        dashboard: DashboardConfig,
        add_type: str,
    ) -> None:
        initial_position = dashlet_registry[add_type].initial_position()
        # Add a static vertical offset to reduce the chance of placing the new widget in a way
        # where it covers existing widgets
        y_offset = 5 if len(dashboard["dashlets"]) > 0 else 0
        dashlet_spec["position"] = (initial_position[0], initial_position[1] + y_offset)
        dashlet_spec["size"] = dashlet_registry[add_type].initial_size()

    def _update_dashlet_spec(
        self,
        dashlet_spec: DashletConfig,
        dashboard: DashboardConfig,
        add_type: str,
    ) -> None:
        """Allow subclasses to update the dashlet spec before adding it to the dashboard."""
        if dashboard_uses_relative_grid(dashboard):
            self._add_relative_grid_layout_to_dashlet_spec(dashlet_spec, dashboard, add_type)
        else:
            raise ValueError("Unexpected layout type for dashboard")

    @staticmethod
    def _create_embedded_view_spec_and_dashlet(
        dashlet_spec: ViewDashletConfig,
    ) -> tuple[DashboardEmbeddedViewSpec, EmbeddedViewDashletConfig]:
        embedded_view_id = str(uuid.uuid4())

        view_spec: DashboardEmbeddedViewSpec = {
            "single_infos": dashlet_spec["single_infos"],
            "datasource": dashlet_spec["datasource"],
            "layout": dashlet_spec["layout"],
            "group_painters": dashlet_spec["group_painters"],
            "painters": dashlet_spec["painters"],
            "browser_reload": dashlet_spec["browser_reload"],
            "num_columns": dashlet_spec["num_columns"],
            "column_headers": dashlet_spec["column_headers"],
            "sorters": dashlet_spec["sorters"],
        }

        if "add_headers" in dashlet_spec:
            view_spec["add_headers"] = dashlet_spec["add_headers"]

        if "mobile" in dashlet_spec:
            view_spec["mobile"] = dashlet_spec["mobile"]

        if "mustsearch" in dashlet_spec:
            view_spec["mustsearch"] = dashlet_spec["mustsearch"]

        if "force_checkboxes" in dashlet_spec:
            view_spec["force_checkboxes"] = dashlet_spec["force_checkboxes"]

        if "user_sortable" in dashlet_spec:
            view_spec["user_sortable"] = dashlet_spec["user_sortable"]

        if "play_sounds" in dashlet_spec:
            view_spec["play_sounds"] = dashlet_spec["play_sounds"]

        if "inventory_join_macros" in dashlet_spec:
            view_spec["inventory_join_macros"] = dashlet_spec["inventory_join_macros"]

        if "modified_at" in dashlet_spec:
            view_spec["modified_at"] = dashlet_spec["modified_at"]

        embedded_view_dashlet = EmbeddedViewDashletConfig(
            {
                "type": "embedded_view",
                "show_title": True,  # Defaults to True for now
                "name": embedded_view_id,
                "datasource": dashlet_spec["datasource"],
            }
        )

        if "size" in dashlet_spec and "position" in dashlet_spec:
            embedded_view_dashlet["size"] = dashlet_spec["size"]
            embedded_view_dashlet["position"] = dashlet_spec["position"]
        elif "responsive_grid_layouts" in dashlet_spec:
            embedded_view_dashlet["responsive_grid_layouts"] = dashlet_spec[
                "responsive_grid_layouts"
            ]
        else:
            raise ValueError("Dashlet spec has no layout information")

        if "context" in dashlet_spec:
            embedded_view_dashlet["context"] = dashlet_spec["context"]

        if "title" in dashlet_spec:
            embedded_view_dashlet["title"] = dashlet_spec["title"]

        if "title_url" in dashlet_spec:
            embedded_view_dashlet["title_url"] = dashlet_spec["title_url"]

        return view_spec, embedded_view_dashlet
