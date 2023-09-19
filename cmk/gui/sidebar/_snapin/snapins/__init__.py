#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .. import SnapinRegistry
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
from .bookmarks import Bookmarks
from .dashboards import Dashboards
from .groups import HostGroups, ServiceGroups
from .master_control import MasterControlSnapin
from .nagvis_maps import NagVisMaps
from .performance import Performance
from .search import QuicksearchSnapin
from .server_time import CurrentTime
from .site_status import SiteStatus
from .speedometer import Speedometer
from .tactical_overview import TacticalOverviewSnapin
from .views import Views


def register(snapin_registry: SnapinRegistry) -> None:
    snapin_registry.register(Bookmarks)
    snapin_registry.register(Dashboards)
    snapin_registry.register(HostGroups)
    snapin_registry.register(ServiceGroups)
    snapin_registry.register(MasterControlSnapin)
    snapin_registry.register(NagVisMaps)
    snapin_registry.register(Performance)
    snapin_registry.register(QuicksearchSnapin)
    snapin_registry.register(CurrentTime)
    snapin_registry.register(SiteStatus)
    snapin_registry.register(Speedometer)
    snapin_registry.register(TacticalOverviewSnapin)
    snapin_registry.register(Views)
