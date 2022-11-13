#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.version as cmk_version

from cmk.gui.i18n import _, _l
from cmk.gui.plugins.dashboard.stats import StatsDashletConfig
from cmk.gui.plugins.dashboard.utils import (
    builtin_dashboards,
    DashboardConfig,
    GROW,
    LinkedViewDashletConfig,
    MAX,
    ViewDashletConfig,
)
from cmk.gui.type_defs import PainterSpec, SorterSpec, VisualLinkSpec

builtin_dashboards["problems"] = DashboardConfig(
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
                    "show_title": True,
                    "context": {
                        "wato_folder": {
                            "wato_folder": "",
                        }
                    },
                    "single_infos": [],
                }
            ),
            StatsDashletConfig(
                {
                    "title": _("Service statistics"),
                    "type": "servicestats",
                    "position": (31, 1),
                    "show_title": True,
                    "context": {
                        "wato_folder": {
                            "wato_folder": "",
                        }
                    },
                    "single_infos": [],
                }
            ),
            ViewDashletConfig(
                {
                    "type": "view",
                    "title": _("Host Problems (unhandled)"),
                    "title_url": "view.py?view_name=hostproblems&is_host_acknowledged=0",
                    "description": "",
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
                    "hidden": True,
                    "hidebutton": True,
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_2",
                    "num_columns": 1,
                    "owner": "",
                    "painters": [
                        PainterSpec(name="host_state"),
                        PainterSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="host"),
                        ),
                        PainterSpec(name="host_icons"),
                        PainterSpec(name="host_state_age"),
                        PainterSpec(name="host_plugin_output"),
                    ],
                    "public": True,
                    "sorters": [SorterSpec(sorter="hoststate", negate=True)],
                    "topic": "",
                    "link_from": {},
                    "icon": None,
                    "add_context_to_title": True,
                    "sort_index": 99,
                    "is_show_more": False,
                }
            ),
            ViewDashletConfig(
                {
                    "type": "view",
                    "title": _("Service Problems (unhandled)"),
                    "title_url": "view.py?view_name=svcproblems&is_service_acknowledged=0",
                    "description": "",
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
                    "hidden": True,
                    "hidebutton": False,
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_3",
                    "num_columns": 1,
                    "owner": "",
                    "painters": [
                        PainterSpec(name="service_state"),
                        PainterSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="host"),
                        ),
                        PainterSpec(
                            name="service_description",
                            link_spec=VisualLinkSpec(type_name="views", name="service"),
                        ),
                        PainterSpec(name="service_icons"),
                        PainterSpec(name="svc_plugin_output"),
                        PainterSpec(name="svc_state_age"),
                        PainterSpec(name="svc_check_age"),
                    ],
                    "play_sounds": True,
                    "public": True,
                    "sorters": [
                        SorterSpec(sorter="svcstate", negate=True),
                        SorterSpec(sorter="stateage", negate=False),
                        SorterSpec(sorter="svcdescr", negate=False),
                    ],
                    "link_from": {},
                    "topic": "",
                    "icon": None,
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
                    "description": "",
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
                    "hidden": True,
                    "hidebutton": False,
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_4",
                    "num_columns": 1,
                    "owner": "admin",
                    "painters": [
                        PainterSpec(name="log_icon"),
                        PainterSpec(name="log_time"),
                        PainterSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="hostsvcevents"),
                        ),
                        PainterSpec(
                            name="service_description",
                            link_spec=VisualLinkSpec(type_name="views", name="svcevents"),
                        ),
                        PainterSpec(name="log_plugin_output"),
                    ],
                    "play_sounds": False,
                    "public": True,
                    "sorters": [SorterSpec(sorter="log_time", negate=True)],
                    "link_from": {},
                    "topic": "",
                    "icon": None,
                    "add_context_to_title": True,
                    "sort_index": 99,
                    "is_show_more": False,
                }
            ),
        ],
        "owner": "",
        "public": True,
        "name": "problems",
        "hidden": False,
        "link_from": {},
        "add_context_to_title": True,
        "is_show_more": False,
    }
)


# CEE uses specific "main" dashboard with new CEE specific dashlets.
# CRE should use the problem dashboard as main dashboard
if cmk_version.is_raw_edition():
    main_dashboard = builtin_dashboards["main"] = builtin_dashboards.pop("problems")
    main_dashboard["title"] = _l("Main dashboard")
    main_dashboard["icon"] = "dashboard_main"
    main_dashboard["topic"] = "overview"
    main_dashboard["sort_index"] = 12

builtin_dashboards["simple_problems"] = DashboardConfig(
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
                    "description": "",
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
                    "hidden": True,
                    "hidebutton": True,
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_0",
                    "num_columns": 1,
                    "owner": "",
                    "painters": [
                        PainterSpec(name="host_state"),
                        PainterSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="host"),
                        ),
                        PainterSpec(name="host_icons"),
                        PainterSpec(name="host_state_age"),
                        PainterSpec(name="host_plugin_output"),
                    ],
                    "public": True,
                    "sorters": [SorterSpec(sorter="hoststate", negate=True)],
                    "topic": "",
                    "link_from": {},
                    "icon": None,
                    "add_context_to_title": True,
                    "sort_index": 99,
                    "is_show_more": False,
                }
            ),
            ViewDashletConfig(
                {
                    "type": "view",
                    "title": _("Service Problems (unhandled)"),
                    "title_url": "view.py?view_name=svcproblems&is_service_acknowledged=0",
                    "description": "",
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
                    "hidden": True,
                    "hidebutton": False,
                    "layout": "table",
                    "mustsearch": False,
                    "name": "dashlet_1",
                    "num_columns": 1,
                    "owner": "",
                    "painters": [
                        PainterSpec(name="service_state"),
                        PainterSpec(
                            name="host",
                            link_spec=VisualLinkSpec(type_name="views", name="host"),
                        ),
                        PainterSpec(
                            name="service_description",
                            link_spec=VisualLinkSpec(type_name="views", name="service"),
                        ),
                        PainterSpec(name="service_icons"),
                        PainterSpec(name="svc_plugin_output"),
                        PainterSpec(name="svc_state_age"),
                        PainterSpec(name="svc_check_age"),
                    ],
                    "play_sounds": True,
                    "public": True,
                    "sorters": [
                        SorterSpec(sorter="svcstate", negate=True),
                        SorterSpec(sorter="stateage", negate=False),
                        SorterSpec(sorter="svcdescr", negate=False),
                    ],
                    "link_from": {},
                    "topic": "",
                    "icon": None,
                    "add_context_to_title": True,
                    "sort_index": 99,
                    "is_show_more": False,
                }
            ),
        ],
        "owner": "",
        "public": True,
        "name": "simple_problems",
        "hidden": False,
        "link_from": {},
        "add_context_to_title": True,
        "is_show_more": False,
    }
)

builtin_dashboards["checkmk"] = DashboardConfig(
    {
        "mandatory_context_filters": [],
        "topic": "analyze",
        "sort_index": 5,
        "hidebutton": False,
        "title": _l("Checkmk dashboard"),
        "description": _l("Displays an overview of all Checkmk servers and instances\n"),
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
        "owner": "",
        "public": True,
        "name": "checkmk",
        "is_show_more": False,
    }
)
