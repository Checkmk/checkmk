#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# FIXME: Can be removed once all dashboards have been converted
# to have the view definitions right inside the dashboards

from cmk.gui.i18n import _l
from cmk.gui.type_defs import PainterSpec, SorterSpec, VisualLinkSpec
from cmk.gui.view_store import multisite_builtin_views

multisite_builtin_views.update(
    {
        # A similar view, used in the dashboard
        "hostproblems_dash": {
            "browser_reload": 30,
            "column_headers": "pergroup",
            "datasource": "hosts",
            "description": _l(
                "A complete list of all host problems, optimized for usage in the dashboard"
            ),
            "group_painters": [],
            "hidden": True,
            "hidebutton": True,
            "layout": "table",
            "mustsearch": False,
            "name": "hostproblems_dash",
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
            "title": _l("Host problems"),
            "topic": None,
            "user_sortable": True,
            "single_infos": [],
            "context": {
                "host_scheduled_downtime_depth": {"is_host_scheduled_downtime_depth": "0"},
                "hoststate": {"hst0": "", "hst1": "on", "hst2": "on", "hstp": ""},
                "host_acknowledged": {"is_host_acknowledged": "0"},
            },
            "link_from": {},
            "icon": None,
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
        },
        # Similar view, but for the dashboard
        "svcproblems_dash": {
            "browser_reload": 30,
            "column_headers": "pergroup",
            "datasource": "services",
            "description": _l(
                "All non-downtime, non-acknownledged services, used for the dashbaord"
            ),
            "group_painters": [],
            "hidden": True,
            "layout": "table",
            "mustsearch": False,
            "name": "svcproblems_dash",
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
            "title": _l("Service problems"),
            "topic": None,
            "user_sortable": True,
            "single_infos": [],
            "context": {
                "service_acknowledged": {"is_service_acknowledged": "0"},
                "svcstate": {"st0": "", "st1": "on", "st2": "on", "st3": "on", "stp": ""},
                "hoststate": {"hst0": "on", "hst1": "", "hst2": "", "hstp": "on"},
                "in_downtime": {"is_in_downtime": "0"},
            },
            "link_from": {},
            "icon": None,
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
        },
        # Similar view, but for dashboard
        "events_dash": {
            "browser_reload": 90,
            "column_headers": "pergroup",
            "datasource": "log_events",
            "description": _l("Events of the last 4 hours."),
            "group_painters": [],
            "hidden": True,
            "layout": "table",
            "mustsearch": False,
            "name": "events_dash",
            "num_columns": 1,
            "owner": "",
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
            "sorters": [],
            "title": _l("Events of the last 4 hours (for the dashboard)"),
            "topic": None,
            "user_sortable": True,
            "single_infos": [],
            "context": {"logtime": {"logtime_from": "4", "logtime_from_range": "3600"}},
            "link_from": {},
            "icon": None,
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
        },
    }
)
