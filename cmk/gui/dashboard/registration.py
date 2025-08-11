#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.permissions import PermissionSection, PermissionSectionRegistry
from cmk.gui.valuespec import AutocompleterRegistry
from cmk.gui.visuals.type import VisualTypeRegistry
from cmk.gui.watolib.groups import ContactGroupUsageFinderRegistry

from ._find_group_usage import find_usages_of_contact_group_in_dashboards
from .builtin_dashboards import builtin_dashboards
from .cre_dashboards import register_builtin_dashboards
from .dashlet import DashletRegistry, FigureDashletPage, register_dashlets
from .page_create_dashboard import page_create_dashboard
from .page_create_view_dashlet import (
    page_create_link_view_dashlet,
    page_create_view_dashlet,
    page_create_view_dashlet_infos,
)
from .page_edit_dashboard import page_edit_dashboard
from .page_edit_dashboard_actions import ajax_dashlet_pos, page_clone_dashlet, page_delete_dashlet
from .page_edit_dashboards import page_edit_dashboards
from .page_edit_dashlet import EditDashletPage
from .page_show_dashboard import ajax_dashlet, AjaxInitialDashboardFilters, page_dashboard
from .visual_type import VisualTypeDashboards


def register(
    permission_section_registry: PermissionSectionRegistry,
    page_registry: PageRegistry,
    visual_type_registry: VisualTypeRegistry,
    dashlet_registry_: DashletRegistry,
    contact_group_usage_finder_registry: ContactGroupUsageFinderRegistry,
    autocompleter_registry: AutocompleterRegistry,
) -> None:
    visual_type_registry.register(VisualTypeDashboards)
    permission_section_registry.register(PERMISSION_SECTION_DASHBOARD)

    page_registry.register(PageEndpoint("ajax_figure_dashlet_data", FigureDashletPage))
    page_registry.register(
        PageEndpoint("ajax_initial_dashboard_filters", AjaxInitialDashboardFilters)
    )
    page_registry.register(PageEndpoint("edit_dashlet", EditDashletPage))
    page_registry.register(PageEndpoint("delete_dashlet", page_delete_dashlet))
    page_registry.register(PageEndpoint("dashboard", page_dashboard))
    page_registry.register(PageEndpoint("dashboard_dashlet", ajax_dashlet))
    page_registry.register(PageEndpoint("edit_dashboards", page_edit_dashboards))
    page_registry.register(PageEndpoint("create_dashboard", page_create_dashboard))
    page_registry.register(PageEndpoint("edit_dashboard", page_edit_dashboard))
    page_registry.register(PageEndpoint("create_link_view_dashlet", page_create_link_view_dashlet))
    page_registry.register(PageEndpoint("create_view_dashlet", page_create_view_dashlet))
    page_registry.register(
        PageEndpoint("create_view_dashlet_infos", page_create_view_dashlet_infos)
    )
    page_registry.register(PageEndpoint("clone_dashlet", page_clone_dashlet))
    page_registry.register(PageEndpoint("delete_dashlet", page_delete_dashlet))
    page_registry.register(PageEndpoint("ajax_dashlet_pos", ajax_dashlet_pos))

    register_dashlets(dashlet_registry_, autocompleter_registry)
    register_builtin_dashboards(builtin_dashboards)
    contact_group_usage_finder_registry.register(find_usages_of_contact_group_in_dashboards)


PERMISSION_SECTION_DASHBOARD = PermissionSection(
    name="dashboard",
    title=_("Dashboards"),
    do_sort=True,
)
