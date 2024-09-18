#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc import version
from cmk.ccc.version import edition_supports_nagvis

from cmk.utils import paths

from cmk.gui.pages import PageRegistry

from ._base import CustomizableSidebarSnapin as CustomizableSidebarSnapin
from ._base import PageHandlers as PageHandlers
from ._base import SidebarSnapin as SidebarSnapin
from ._bookmarks import Bookmarks
from ._dashboards import Dashboards
from ._groups import HostGroups, ServiceGroups
from ._helpers import begin_footnote_links as begin_footnote_links
from ._helpers import bulletlink as bulletlink
from ._helpers import end_footnote_links as end_footnote_links
from ._helpers import footnotelinks as footnotelinks
from ._helpers import heading as heading
from ._helpers import iconlink as iconlink
from ._helpers import link as link
from ._helpers import make_topic_menu as make_topic_menu
from ._helpers import render_link as render_link
from ._helpers import show_topic_menu as show_topic_menu
from ._helpers import snapin_site_choice as snapin_site_choice
from ._helpers import snapin_width as snapin_width
from ._helpers import write_snapin_exception as write_snapin_exception
from ._master_control import MasterControlSnapin
from ._nagvis_maps import NagVisMaps
from ._performance import Performance
from ._permission_section import PermissionSectionSidebarSnapins as PermissionSectionSidebarSnapins
from ._registry import snapin_registry as snapin_registry
from ._registry import SnapinRegistry as SnapinRegistry
from ._search import PageSearchMonitoring, PageSearchSetup, QuicksearchSnapin
from ._server_time import CurrentTime
from ._site_status import SiteStatus
from ._speedometer import Speedometer
from ._tactical_overview import TacticalOverviewSnapin
from ._views import ajax_export_views, Views


def register(snapin_registry_: SnapinRegistry, page_registry: PageRegistry) -> None:
    snapin_registry_.register(Bookmarks)
    snapin_registry_.register(Dashboards)
    snapin_registry_.register(HostGroups)
    snapin_registry_.register(ServiceGroups)
    snapin_registry_.register(MasterControlSnapin)
    if edition_supports_nagvis(version.edition(paths.omd_root)):
        snapin_registry_.register(NagVisMaps)
    snapin_registry_.register(Performance)
    snapin_registry_.register(QuicksearchSnapin)
    snapin_registry_.register(CurrentTime)
    snapin_registry_.register(SiteStatus)
    snapin_registry_.register(Speedometer)
    snapin_registry_.register(TacticalOverviewSnapin)
    snapin_registry_.register(Views)
    page_registry.register_page_handler("export_views", ajax_export_views)
    page_registry.register_page("ajax_search_monitoring")(PageSearchMonitoring)
    page_registry.register_page("ajax_search_setup")(PageSearchSetup)
