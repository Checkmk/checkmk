#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator
from typing import cast

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.graphing._graph_specification import GraphSpecification, parse_raw_graph_specification
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.gui.http import response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_javascript_link, PageMenuEntry
from cmk.gui.type_defs import VisualContext
from cmk.gui.visuals.type import VisualType

from .dashlet import copy_view_into_dashlet, dashlet_registry, DashletConfig, ViewDashletConfig
from .store import add_dashlet, get_permitted_dashboards, load_dashboard
from .type_defs import ABCGraphDashletConfig


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
                title=str(board["title"]),
                icon_name="dashboard",
                item=make_javascript_link(
                    "cmk.popup_menu.add_to_visual('dashboards', %s)" % json.dumps(name)
                ),
            )

    def add_visual_handler(
        self,
        target_visual_name: str,
        add_type: str,
        context: VisualContext | None,
        parameters: dict,
    ) -> None:
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

        dashlet_spec = DashletConfig(
            {
                "type": add_type,
                "position": dashlet_registry[add_type].initial_position(),
                "size": dashlet_registry[add_type].initial_size(),
                "show_title": True,
            }
        )

        dashlet_spec["context"] = context
        if add_type == "view":
            view_name = parameters["name"]
        else:
            # We don't know if what we get as parameters actually fits a DashletConfig.
            dashlet_spec.update(parameters)  # type: ignore[typeddict-item]

        # When a view shall be added to the dashboard, load the view and put it into the dashlet
        # FIXME: Move this to the dashlet plugins
        if add_type == "view":
            dashlet_spec = cast(ViewDashletConfig, dashlet_spec)
            # save the original context and override the context provided by the view
            context = dashlet_spec["context"]
            copy_view_into_dashlet(
                dashlet_spec, len(dashboard["dashlets"]), view_name, add_context=context
            )

        elif add_type in ["pnpgraph", "custom_graph"]:
            dashlet_spec = cast(ABCGraphDashletConfig, dashlet_spec)

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
