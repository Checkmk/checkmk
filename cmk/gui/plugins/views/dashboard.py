#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# FIXME: Can be removed once all dashboards have been converted
# to have the view definitions right inside the dashboards

from cmk.gui.plugins.views.utils import multisite_builtin_views

multisite_builtin_views.update(
    {
        # A similar view, used in the dashboard
        "hostproblems_dash": {
            "browser_reload": 30,
            "column_headers": "pergroup",
            "datasource": "hosts",
            "description": "A complete list of all host problems, optimized for usage in the dashboard",
            "group_painters": [],
            "hard_filters": [
                "host_scheduled_downtime_depth",
                "hoststate",
                "host_acknowledged",
            ],
            "hard_filtervars": [
                ("is_host_scheduled_downtime_depth", "0"),
                ("hst0", ""),
                ("hst1", "on"),
                ("hst2", "on"),
                ("hstp", ""),
                ("is_host_acknowledged", "0"),
            ],
            "hidden": True,
            "hidebutton": True,
            "hide_filters": [],
            "layout": "table",
            "mustsearch": False,
            "name": "hostproblems",
            "num_columns": 1,
            "owner": "",
            "painters": [
                ("host_state", None),
                ("host", "host"),
                ("host_icons", None),
                ("host_state_age", None),
                ("host_plugin_output", None),
                # ('host_check_age', None),       # save space
                # ('num_services_ok', 'host_ok'), # save space
                # ('num_services_warn', 'host_warn'),
                # ('num_services_crit', 'host_crit'),
                # ('num_services_unknown', 'host_unknown'),
                # ('num_services_pending', 'host_pending'),
            ],
            "public": True,
            "show_filters": [],
            "sorters": [("hoststate", True)],
            "title": "Host problems",
            "topic": None,
        },
        # Similar view, but for the dashboard
        "svcproblems_dash": {
            "browser_reload": 30,
            "column_headers": "pergroup",
            "datasource": "services",
            "description": "All non-downtime, non-acknownledged services, used for the dashbaord",
            "group_painters": [],
            "hard_filters": ["service_acknowledged", "svcstate", "hoststate", "in_downtime"],
            "hard_filtervars": [
                ("is_in_downtime", "0"),
                ("is_service_acknowledged", "0"),
                ("st0", ""),
                ("st1", "on"),
                ("st2", "on"),
                ("st3", "on"),
                ("stp", ""),
                ("hst0", "on"),
                ("hst1", ""),
                ("hst2", ""),
                ("hstp", "on"),
            ],
            "hidden": True,
            "hide_filters": [],
            "layout": "table",
            "mustsearch": False,
            "name": "svcproblems",
            "num_columns": 1,
            "owner": "",
            "painters": [
                ("service_state", None),
                ("host", "host"),
                ("service_description", "service"),
                ("service_icons", None),
                ("svc_plugin_output", None),
                ("svc_state_age", None),
                ("svc_check_age", None),
                # ('perfometer', None),
            ],
            "play_sounds": True,
            "public": True,
            "show_filters": [],
            "sorters": [
                ("svcstate", True),
                ("stateage", False),
                ("svcdescr", False),
            ],
            "title": "Service problems",
            "topic": None,
        },
        # Similar view, but for dashboard
        "events_dash": {
            "browser_reload": 90,
            "column_headers": "pergroup",
            "datasource": "log_events",
            "description": "Events of the last 4 hours.",
            "group_painters": [],
            "hard_filters": ["logtime"],
            "hard_filtervars": [
                ("logtime_from_range", "3600"),
                ("logtime_from", "4"),
            ],
            "hidden": True,
            "hide_filters": [],
            "layout": "table",
            "mustsearch": False,
            "name": "events_dash",
            "num_columns": 1,
            "owner": "admin",
            "painters": [
                ("log_icon", None),
                ("log_time", None),
                # ('log_type', None),
                ("host", "hostsvcevents"),
                ("service_description", "svcevents"),
                # ('log_state_type', None),
                ("log_plugin_output", None),
            ],
            "play_sounds": False,
            "public": True,
            "show_filters": [],
            "sorters": [],
            "title": "Events of the last 4 hours (for the dashboard)",
            "topic": None,
        },
    }
)
