#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.openapi.framework import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.permissions import PermissionSection, PermissionSectionRegistry
from cmk.gui.token_auth import TokenAuthenticatedEndpoint, TokenAuthenticatedPageRegistry
from cmk.gui.valuespec import AutocompleterRegistry
from cmk.gui.visuals.type import VisualTypeRegistry
from cmk.gui.watolib.groups import ContactGroupUsageFinderRegistry

from ._find_group_usage import find_usages_of_contact_group_in_dashboards
from .api import register_endpoints
from .builtin_dashboards import builtin_dashboards
from .community_dashboards import register_builtin_dashboards
from .dashlet import DashletRegistry, register_dashlets
from .page_check_token_validity import CheckTokenValidityPage
from .page_edit_dashboard import page_edit_dashboard
from .page_edit_dashboards import page_edit_dashboards, PAGE_EDIT_DASHBOARDS_LINK
from .page_figure_widget import FigureWidgetPage, FigureWidgetTokenAuthPage
from .page_graph_hover import GraphHoverTokenAuthPage
from .page_graph_widget import GraphWidgetPage, GraphWidgetTokenAuthPage
from .page_show_dashboard import page_dashboard_app
from .page_show_shared_dashboard import SharedDashboardPage
from .page_view_widget import (
    ViewWidgetEditPage,
    ViewWidgetIFramePage,
    ViewWidgetIFrameTokenPage,
)
from .visual_type import VisualTypeDashboards


def register(
    permission_section_registry: PermissionSectionRegistry,
    page_registry: PageRegistry,
    token_authenticated_page_registry: TokenAuthenticatedPageRegistry,
    visual_type_registry: VisualTypeRegistry,
    dashlet_registry_: DashletRegistry,
    contact_group_usage_finder_registry: ContactGroupUsageFinderRegistry,
    autocompleter_registry: AutocompleterRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    ignore_duplicate_endpoints: bool = False,
) -> None:
    visual_type_registry.register(VisualTypeDashboards)
    permission_section_registry.register(PERMISSION_SECTION_DASHBOARD)

    page_registry.register(PageEndpoint(FigureWidgetPage.ident(), FigureWidgetPage()))
    page_registry.register(PageEndpoint("widget_graph", GraphWidgetPage()))
    page_registry.register(PageEndpoint("widget_iframe_view", ViewWidgetIFramePage()))
    page_registry.register(PageEndpoint("widget_edit_view", ViewWidgetEditPage()))
    page_registry.register(PageEndpoint("dashboard", page_dashboard_app))
    token_authenticated_page_registry.register(
        TokenAuthenticatedEndpoint("shared_dashboard", SharedDashboardPage())
    )
    page_registry.register(PageEndpoint("edit_dashboard", page_edit_dashboard))
    page_registry.register(PageEndpoint(PAGE_EDIT_DASHBOARDS_LINK, page_edit_dashboards))

    token_authenticated_page_registry.register(
        TokenAuthenticatedEndpoint(FigureWidgetTokenAuthPage.ident(), FigureWidgetTokenAuthPage())
    )
    token_authenticated_page_registry.register(
        TokenAuthenticatedEndpoint(GraphWidgetTokenAuthPage.ident(), GraphWidgetTokenAuthPage())
    )
    token_authenticated_page_registry.register(
        TokenAuthenticatedEndpoint("widget_iframe_view_token_auth", ViewWidgetIFrameTokenPage())
    )
    token_authenticated_page_registry.register(
        TokenAuthenticatedEndpoint(GraphHoverTokenAuthPage.ident(), GraphHoverTokenAuthPage())
    )
    token_authenticated_page_registry.register(
        TokenAuthenticatedEndpoint("check_token_validity", CheckTokenValidityPage())
    )

    register_dashlets(dashlet_registry_, autocompleter_registry)
    register_builtin_dashboards(builtin_dashboards)
    contact_group_usage_finder_registry.register(find_usages_of_contact_group_in_dashboards)
    register_endpoints(
        endpoint_family_registry,
        versioned_endpoint_registry,
        ignore_duplicates=ignore_duplicate_endpoints,
    )


PERMISSION_SECTION_DASHBOARD = PermissionSection(
    name="dashboard",
    title=_("Dashboards"),
    do_sort=True,
)
