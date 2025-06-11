#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.ccc.version as cmk_version
from cmk.ccc.user import UserId

from cmk.utils import paths

from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import ColumnSpec, SorterSpec, VisualLinkSpec

from .builtin_dashboards import GROW, MAX
from .dashlet import LinkedViewDashletConfig, StatsDashletConfig, ViewDashletConfig
from .type_defs import DashboardConfig, DashboardName


def register_builtin_dashboards(builtin: dict[DashboardName, DashboardConfig]) -> None:
    builtin["problems"] = ProblemsDashboard

    # CEE uses specific "main" dashboard with new CEE specific dashlets.
    # CRE should use the problem dashboard as main dashboard
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CRE:
        main_dashboard = builtin["main"] = builtin.pop("problems")
        main_dashboard["title"] = _l("Main dashboard")
        main_dashboard["icon"] = "dashboard_main"
        main_dashboard["topic"] = "overview"
        main_dashboard["sort_index"] = 12

    builtin["simple_problems"] = SimpleProblemsDashboard
    builtin["checkmk"] = CheckmkOverviewDashboard


ProblemsDashboard = DashboardConfig(
    {
        "mandatory_context_filters": [],
        "hidebutton": False,
        "single_infos": [],
        "context": {},
        "mtime": 0,
        "show_title": True,
        "title": _l("Problem dashboard"),
        "topic": "problems",
        "sort_index": 5,
        "icon": "dashboard_problems",
        "description": _l(
            "This dashboard gives you a general overview on the state of your monitored devices."
        ),
        "dashlets": [
            StatsDashletConfig(
                {
                    "title": _("Host statistics"),
                    "type": "hoststats",
                    "position": (1, 1),
                    "size": (30, 18),
                    "show_title": True,
                    "context": {},
                    "single_infos": [],
                }
            ),
            StatsDashletConfig(
                {
                    "title": _("Service statistics"),
                    "type": "servicestats",
                    "position": (31, 1),
                    "size": (30, 18),
                    "show_title": True,
                    "context": {},
                    "single_infos": [],
                }
            ),
            ViewDashletConfig(
                {
                    "type": "view",
                    "title": _("Host Problems (unhandled)"),
                    "title_url": "view.py?view_name=hostproblems&is_host_acknowledged=0",
                    "position": (-1, 1),
                    "size": (GROW, 18),
                    "show_title": True,
                    "browser_reload": 30,
                    "column_headers": "pergroup",
                    "datasource": "hosts",
                    "single_infos": [],
                    "group_painters": [],
                    "context": {
                        "hoststate": {
                            "hst0": "",
                            "hst1": "on",
                            "hst2": "on",
                            "hstp": "",
                        },
                        "host_acknowledged": {"is_host_acknowledged": "0"},
                        "host_scheduled_downtime_depth": {"is_host_scheduled_downtime_depth": "0"},
                    },
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_2",
                    "num_columns": 1,
                    "painters": [
                        ColumnSpec(name="host_state"),
                        ColumnSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="host"),
                        ),
                        ColumnSpec(name="host_icons"),
                        ColumnSpec(name="host_state_age"),
                        ColumnSpec(name="host_plugin_output"),
                    ],
                    "sorters": [SorterSpec(sorter="hoststate", negate=True)],
                    "add_context_to_title": True,
                    "sort_index": 99,
                    "is_show_more": False,
                }
            ),
            ViewDashletConfig(
                {
                    "type": "view",
                    "title": _("Service problems (unhandled)"),
                    "title_url": "view.py?view_name=svcproblems&is_service_acknowledged=0",
                    "position": (1, 19),
                    "size": (GROW, MAX),
                    "show_title": True,
                    "browser_reload": 30,
                    "column_headers": "pergroup",
                    "datasource": "services",
                    "single_infos": [],
                    "group_painters": [],
                    "context": {
                        "service_acknowledged": {"is_service_acknowledged": "0"},
                        "in_downtime": {"is_in_downtime": "0"},
                        "hoststate": {"hst0": "on", "hst1": "", "hst2": "", "hstp": "on"},
                        "svcstate": {
                            "st0": "",
                            "st1": "on",
                            "st2": "on",
                            "st3": "on",
                            "stp": "",
                        },
                    },
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_3",
                    "num_columns": 1,
                    "painters": [
                        ColumnSpec(name="service_state"),
                        ColumnSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="host"),
                        ),
                        ColumnSpec(
                            name="service_description",
                            link_spec=VisualLinkSpec(type_name="views", name="service"),
                        ),
                        ColumnSpec(name="service_icons"),
                        ColumnSpec(name="svc_plugin_output"),
                        ColumnSpec(name="svc_state_age"),
                        ColumnSpec(name="svc_check_age"),
                    ],
                    "play_sounds": True,
                    "sorters": [
                        SorterSpec(sorter="svcstate", negate=True),
                        SorterSpec(sorter="stateage", negate=False),
                        SorterSpec(sorter="svcdescr", negate=False),
                    ],
                    "add_context_to_title": True,
                    "sort_index": 99,
                    "is_show_more": False,
                }
            ),
            ViewDashletConfig(
                {
                    "type": "view",
                    "title": _("Events of recent 4 hours"),
                    "title_url": "view.py?view_name=events_dash",
                    "position": (-1, -1),
                    "size": (GROW, GROW),
                    "show_title": True,
                    "browser_reload": 90,
                    "column_headers": "pergroup",
                    "datasource": "log_events",
                    "single_infos": [],
                    "group_painters": [],
                    "context": {
                        "logtime": {
                            "logtime_from_range": "3600",
                            "logtime_from": "4",
                        },
                    },
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_4",
                    "num_columns": 1,
                    "painters": [
                        ColumnSpec(name="log_icon"),
                        ColumnSpec(name="log_time"),
                        ColumnSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="hostsvcevents"),
                        ),
                        ColumnSpec(
                            name="service_description",
                            link_spec=VisualLinkSpec(type_name="views", name="svcevents"),
                        ),
                        ColumnSpec(name="log_plugin_output"),
                    ],
                    "play_sounds": False,
                    "sorters": [SorterSpec(sorter="log_time", negate=True)],
                    "add_context_to_title": True,
                    "sort_index": 99,
                    "is_show_more": False,
                }
            ),
        ],
        "owner": UserId.builtin(),
        "public": True,
        "name": "problems",
        "hidden": False,
        "link_from": {},
        "add_context_to_title": True,
        "is_show_more": False,
        "packaged": False,
        "main_menu_search_terms": [],
    }
)

SimpleProblemsDashboard = DashboardConfig(
    {
        "mandatory_context_filters": [],
        "hidebutton": False,
        "single_infos": [],
        "context": {},
        "mtime": 0,
        "show_title": True,
        "title": _l("Host & service problems"),
        "topic": "problems",
        "icon": "host_svc_problems",
        "sort_index": 10,
        "description": _l(
            "A compact dashboard which lists your unhandled host and service problems."
        ),
        "dashlets": [
            ViewDashletConfig(
                {
                    "type": "view",
                    "title": _("Host Problems (unhandled)"),
                    "title_url": "view.py?view_name=hostproblems&is_host_acknowledged=0",
                    "show_title": True,
                    "position": (1, 1),
                    "size": (GROW, 18),
                    "browser_reload": 30,
                    "column_headers": "pergroup",
                    "datasource": "hosts",
                    "single_infos": [],
                    "group_painters": [],
                    "context": {
                        "host_acknowledged": {"is_host_acknowledged": "0"},
                        "host_scheduled_downtime_depth": {"is_host_scheduled_downtime_depth": "0"},
                        "hoststate": {"hst0": "", "hst1": "on", "hst2": "on", "hstp": ""},
                    },
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_0",
                    "num_columns": 1,
                    "painters": [
                        ColumnSpec(name="host_state"),
                        ColumnSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="host"),
                        ),
                        ColumnSpec(name="host_icons"),
                        ColumnSpec(name="host_state_age"),
                        ColumnSpec(name="host_plugin_output"),
                    ],
                    "sorters": [SorterSpec(sorter="hoststate", negate=True)],
                    "add_context_to_title": True,
                    "sort_index": 99,
                    "is_show_more": False,
                }
            ),
            ViewDashletConfig(
                {
                    "type": "view",
                    "title": _("Service problems (unhandled)"),
                    "title_url": "view.py?view_name=svcproblems&is_service_acknowledged=0",
                    "show_title": True,
                    "position": (1, 19),
                    "size": (GROW, MAX),
                    "browser_reload": 30,
                    "column_headers": "pergroup",
                    "datasource": "services",
                    "single_infos": [],
                    "group_painters": [],
                    "context": {
                        "service_acknowledged": {"is_service_acknowledged": "0"},
                        "in_downtime": {"is_in_downtime": "0"},
                        "hoststate": {"hst0": "on", "hst1": "", "hst2": "", "hstp": "on"},
                        "svcstate": {
                            "st0": "",
                            "st1": "on",
                            "st2": "on",
                            "st3": "on",
                            "stp": "",
                        },
                    },
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_1",
                    "num_columns": 1,
                    "painters": [
                        ColumnSpec(name="service_state"),
                        ColumnSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="host"),
                        ),
                        ColumnSpec(
                            name="service_description",
                            link_spec=VisualLinkSpec(type_name="views", name="service"),
                        ),
                        ColumnSpec(name="service_icons"),
                        ColumnSpec(name="svc_plugin_output"),
                        ColumnSpec(name="svc_state_age"),
                        ColumnSpec(name="svc_check_age"),
                    ],
                    "play_sounds": True,
                    "sorters": [
                        SorterSpec(sorter="svcstate", negate=True),
                        SorterSpec(sorter="stateage", negate=False),
                        SorterSpec(sorter="svcdescr", negate=False),
                    ],
                    "add_context_to_title": True,
                    "sort_index": 99,
                    "is_show_more": False,
                }
            ),
        ],
        "owner": UserId.builtin(),
        "public": True,
        "name": "simple_problems",
        "hidden": False,
        "link_from": {},
        "add_context_to_title": True,
        "is_show_more": False,
        "packaged": False,
        "main_menu_search_terms": [],
    }
)

CheckmkOverviewDashboard = DashboardConfig(
    {
        "mandatory_context_filters": [],
        "topic": "analyze",
        "sort_index": 5,
        "hidebutton": False,
        "title": _l("Checkmk dashboard"),
        "description": _l("Displays an overview of all Checkmk servers and sites\n"),
        "add_context_to_title": False,
        "link_from": {},
        "context": {},
        "hidden": False,
        "mtime": 0,
        "show_title": True,
        "dashlets": [
            LinkedViewDashletConfig(
                {
                    "background": True,
                    "type": "linked_view",
                    "name": "cmk_servers",
                    "context": {},
                    "position": (1, 1),
                    "show_title": True,
                    "single_infos": [],
                    "size": (0, 0),
                }
            ),
            LinkedViewDashletConfig(
                {
                    "name": "cmk_sites",
                    "title": _("Site overview"),
                    "show_title": True,
                    "background": True,
                    "context": {},
                    "position": (1, 47),
                    "type": "linked_view",
                    "single_infos": [],
                    "size": (0, 0),
                }
            ),
        ],
        "single_infos": [],
        "icon": "dashboard_system",
        "owner": UserId.builtin(),
        "public": True,
        "name": "checkmk",
        "is_show_more": False,
        "packaged": False,
        "main_menu_search_terms": [],
    }
)
