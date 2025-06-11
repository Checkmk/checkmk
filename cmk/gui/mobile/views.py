#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from functools import partial
from typing import override

from cmk.ccc.user import UserId

from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.painter.v0 import Cell
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import ColumnSpec, Rows, SorterSpec, ViewSpec, VisualLinkSpec
from cmk.gui.utils.html import HTML
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.views.layout import Layout
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visual_link import render_link_to_view

#   .--Views---------------------------------------------------------------.
#   |                    __     ___                                        |
#   |                    \ \   / (_) _____      _____                      |
#   |                     \ \ / /| |/ _ \ \ /\ / / __|                     |
#   |                      \ V / | |  __/\ V  V /\__ \                     |
#   |                       \_/  |_|\___| \_/\_/ |___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Views optimated for usage in the mobile UI                           |
#   '----------------------------------------------------------------------'


multisite_builtin_views.update(
    {
        # Service search
        "mobile_searchsvc": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidden": False,
            "hidebutton": False,
            "icon": None,
            "public": True,
            "topic": "overview",
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": True,
            "datasource": "services",
            "group_painters": [
                ColumnSpec(
                    name="sitealias",
                    link_spec=VisualLinkSpec(type_name="views", name="sitehosts"),
                ),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="host"),
                ),
            ],
            "layout": "mobilelist",
            "name": "mobile_searchsvc",
            "num_columns": 2,
            "owner": UserId.builtin(),
            "painters": [
                ColumnSpec(name="service_state"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_hoststatus"),
                ),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_service"),
                ),
                ColumnSpec(name="svc_plugin_output"),
                ColumnSpec(name="svc_state_age"),
            ],
            "sorters": [
                SorterSpec(sorter="site", negate=False),
                SorterSpec(sorter="site_host", negate=False),
                SorterSpec(sorter="svcdescr", negate=False),
            ],
            "title": _l("Service search"),
            "single_infos": [],
            "context": {
                "service_in_notification_period": {"is_service_in_notification_period": "-1"},
                "service_notifications_enabled": {"is_service_notifications_enabled": "-1"},
                "host_in_notification_period": {"is_host_in_notification_period": "-1"},
                "in_downtime": {"is_in_downtime": "-1"},
                "service_scheduled_downtime_depth": {"is_service_scheduled_downtime_depth": "-1"},
                "service_acknowledged": {"is_service_acknowledged": "-1"},
                "hostregex": {"host_regex": ""},
                "serviceregex": {"service_regex": ""},
                "hoststate": {},
                "svcstate": {"st0": "on", "st1": "on", "st2": "on", "st3": "on", "stp": "on"},
                "svchardstate": {},
                "opthostgroup": {"opthost_group": ""},
                "output": {"service_output": ""},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # View of all current service problems
        "mobile_svcproblems": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidden": False,
            "hidebutton": False,
            "icon": None,
            "public": True,
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "topic": "problems",
            "datasource": "services",
            "group_painters": [],
            "layout": "mobilelist",
            "name": "mobile_svcproblems",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="service_state"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_hoststatus"),
                ),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_service"),
                ),
                ColumnSpec(name="svc_plugin_output"),
                ColumnSpec(name="svc_state_age"),
            ],
            "sorters": [
                SorterSpec(sorter="svcstate", negate=True),
                SorterSpec(sorter="stateage", negate=False),
                SorterSpec(sorter="svcdescr", negate=False),
            ],
            "title": _l("Service problems (all)"),
            "owner": UserId.builtin(),
            "single_infos": [],
            "context": {
                "in_downtime": {"is_in_downtime": "0"},
                "service_in_notification_period": {},
                "service_acknowledged": {},
                "svcstate": {"st0": "", "st1": "on", "st2": "on", "st3": "on", "stp": ""},
                "svchardstate": {},
                "hoststate": {"hst0": "on", "hst1": "", "hst2": "", "hstp": "on"},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # View of unhandled service problems
        "mobile_svcproblems_unack": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidden": False,
            "hidebutton": False,
            "icon": None,
            "public": True,
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "topic": "problems",
            "datasource": "services",
            "group_painters": [],
            "layout": "mobilelist",
            "name": "mobile_svcproblems_unack",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="service_state"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_hoststatus"),
                ),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_service"),
                ),
                ColumnSpec(name="svc_plugin_output"),
                ColumnSpec(name="svc_state_age"),
            ],
            "sorters": [
                SorterSpec(sorter="svcstate", negate=True),
                SorterSpec(sorter="stateage", negate=False),
                SorterSpec(sorter="svcdescr", negate=False),
            ],
            "title": _l("Service problems (unhandled)"),
            "owner": UserId.builtin(),
            "single_infos": [],
            "context": {
                "in_downtime": {"is_in_downtime": "0"},
                "service_acknowledged": {"is_service_acknowledged": "0"},
                "service_in_notification_period": {"is_service_in_notification_period": "-1"},
                "hoststate": {"hst0": "on", "hst1": "", "hst2": "", "hstp": "on"},
                "svchardstate": {
                    "hdst0": "on",
                    "hdst1": "on",
                    "hdst2": "on",
                    "hdst3": "on",
                    "hdstp": "on",
                },
                "svcstate": {"st0": "", "st1": "on", "st2": "on", "st3": "on", "stp": ""},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # Service details
        "mobile_service": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidebutton": False,
            "icon": None,
            "public": True,
            "topic": "overview",
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "hidden": True,
            "datasource": "services",
            "group_painters": [],
            "layout": "mobilelist",
            "name": "mobile_host",
            "num_columns": 1,
            "painters": [
                ColumnSpec(name="service_state"),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_service"),
                ),
                ColumnSpec(name="svc_plugin_output"),
                ColumnSpec(name="svc_state_age"),
            ],
            "sorters": [
                SorterSpec(sorter="svcstate", negate=True),
                SorterSpec(sorter="stateage", negate=False),
                SorterSpec(sorter="svcdescr", negate=False),
            ],
            "title": _l("Services of host"),
            "owner": UserId.builtin(),
            "single_infos": ["host"],
            "context": {
                "site": {},
                "svcstate": {"st0": "on", "st1": "on", "st2": "on", "st3": "on", "stp": "on"},
                "serviceregex": {},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # All services of one host
        "mobile_host": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidden": True,
            "hidebutton": False,
            "icon": None,
            "public": True,
            "topic": "overview",
            "user_sortable": False,
            "play_sounds": False,
            "datasource": "services",
            "group_painters": [],
            "layout": "mobilelist",
            "name": "mobile_host",
            "num_columns": 1,
            "painters": [
                ColumnSpec(name="service_state"),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_service"),
                ),
                ColumnSpec(name="svc_plugin_output"),
                ColumnSpec(name="svc_state_age"),
            ],
            "sorters": [
                SorterSpec(sorter="svcstate", negate=True),
                SorterSpec(sorter="stateage", negate=False),
                SorterSpec(sorter="svcdescr", negate=False),
            ],
            "title": _l("Services of host"),
            "owner": UserId.builtin(),
            "single_infos": ["host"],
            "context": {
                "site": {},
                "svcstate": {"st0": "on", "st1": "on", "st2": "on", "st3": "on", "stp": "on"},
                "serviceregex": {},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # Host details
        "mobile_hoststatus": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidebutton": False,
            "public": True,
            "topic": "overview",
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "hidden": True,
            "icon": "status",
            "datasource": "hosts",
            "group_painters": [],
            "layout": "mobiledataset",
            "num_columns": 1,
            "painters": [
                ColumnSpec(name="sitealias"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_host"),
                ),
                ColumnSpec(name="alias"),
                ColumnSpec(name="host_state"),
                ColumnSpec(name="host_address"),
                ColumnSpec(name="host_parents"),
                ColumnSpec(name="host_childs"),
                ColumnSpec(name="host_contact_groups"),
                ColumnSpec(name="host_contacts"),
                ColumnSpec(name="host_plugin_output"),
                ColumnSpec(name="host_perf_data"),
                ColumnSpec(name="host_attempt"),
                ColumnSpec(name="host_check_type"),
                ColumnSpec(name="host_state_age"),
                ColumnSpec(name="host_check_age"),
                ColumnSpec(name="host_next_check"),
                ColumnSpec(name="host_next_notification"),
                ColumnSpec(name="host_last_notification"),
                ColumnSpec(name="host_check_latency"),
                ColumnSpec(name="host_check_duration"),
                ColumnSpec(name="host_in_downtime"),
                ColumnSpec(name="host_in_notifper"),
                ColumnSpec(name="host_notifper"),
                ColumnSpec(
                    name="num_services",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_host"),
                ),
                ColumnSpec(name="host_pnpgraph"),
            ],
            "sorters": [],
            "title": _l("Host status"),
            "owner": UserId.builtin(),
            "name": "mobile_hoststatus",
            "single_infos": ["host"],
            "context": {"site": {}},
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # Search hosts
        "mobile_searchhost": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidden": False,
            "hidebutton": False,
            "icon": None,
            "public": True,
            "topic": "overview",
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": True,
            "datasource": "hosts",
            "group_painters": [],
            "layout": "mobilelist",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="host_state"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_host"),
                ),
                ColumnSpec(name="host_plugin_output"),
            ],
            "sorters": [],
            "title": _l("Host search"),
            "owner": UserId.builtin(),
            "name": "mobile_searchhost",
            "single_infos": [],
            "context": {
                "hoststate": {"hst0": "on", "hst1": "on", "hst2": "on", "hstp": "on"},
                "hostregex": {"host_regex": ""},
                "opthostgroup": {"opthost_group": "", "neg_opthost_group": ""},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # List all host problems
        "mobile_hostproblems": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidden": False,
            "hidebutton": False,
            "icon": None,
            "public": True,
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "topic": "problems",
            "datasource": "hosts",
            "group_painters": [ColumnSpec(name="host_state")],
            "layout": "mobilelist",
            "name": "mobile_hostproblems",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="host_state"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_host"),
                ),
                ColumnSpec(name="host_plugin_output"),
            ],
            "sorters": [],
            "title": _l("Host problems (all)"),
            "owner": UserId.builtin(),
            "single_infos": [],
            "context": {
                "host_scheduled_downtime_depth": {"is_host_scheduled_downtime_depth": "0"},
                "host_in_notification_period": {"is_host_in_notification_period": "-1"},
                "hoststate": {"hst0": "", "hst1": "on", "hst2": "on", "hstp": ""},
                "hostregex": {"host_regex": ""},
                "opthostgroup": {"opthost_group": ""},
                "host_acknowledged": {"is_host_acknowledged": "-1"},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # List unhandled host problems
        "mobile_hostproblems_unack": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidden": False,
            "hidebutton": False,
            "icon": None,
            "public": True,
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "topic": "problems",
            "datasource": "hosts",
            "group_painters": [ColumnSpec(name="host_state")],
            "layout": "mobilelist",
            "name": "mobile_hostproblems_unack",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="host_state"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_host"),
                ),
                ColumnSpec(name="host_plugin_output"),
            ],
            "sorters": [],
            "title": _l("Host problems (unhandled)"),
            "owner": UserId.builtin(),
            "single_infos": [],
            "context": {
                "host_scheduled_downtime_depth": {"is_host_scheduled_downtime_depth": "0"},
                "host_acknowledged": {"is_host_acknowledged": "0"},
                "host_in_notification_period": {"is_host_in_notification_period": "-1"},
                "hoststate": {"hst0": "", "hst1": "on", "hst2": "on", "hstp": ""},
                "hostregex": {"host_regex": ""},
                "opthostgroup": {"opthost_group": ""},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # All Nagios Events at all
        "mobile_events": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidden": False,
            "hidebutton": False,
            "icon": None,
            "public": True,
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "topic": "history",
            "datasource": "log_events",
            "group_painters": [],
            "layout": "mobilelist",
            "name": "mobile_events",
            "num_columns": 1,
            "painters": [
                ColumnSpec(name="log_icon"),
                ColumnSpec(name="log_time"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_hostsvcevents"),
                ),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_svcevents"),
                ),
                ColumnSpec(name="log_plugin_output"),
            ],
            "sorters": [
                SorterSpec(sorter="log_time", negate=False),
                SorterSpec(sorter="log_lineno", negate=False),
            ],
            "title": _l("Events"),
            "owner": UserId.builtin(),
            "single_infos": [],
            "context": {"logtime": {"logtime_from": "4", "logtime_from_range": "3600"}},
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # All Notifications at all
        "mobile_notifications": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidden": False,
            "hidebutton": False,
            "public": True,
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "icon": "notifications",
            "topic": "history",
            "datasource": "log",
            "group_painters": [ColumnSpec(name="log_date")],
            "layout": "mobilelist",
            "name": "mobile_notifications",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="log_state"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_hostsvcnotifications"),
                ),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_svcnotifications"),
                ),
                ColumnSpec(name="log_time"),
                ColumnSpec(name="log_contact_name"),
                ColumnSpec(name="log_type"),
                ColumnSpec(name="log_plugin_output"),
            ],
            "sorters": [
                SorterSpec(sorter="log_time", negate=True),
                SorterSpec(sorter="log_lineno", negate=True),
            ],
            "title": _l("History"),
            "owner": UserId.builtin(),
            "single_infos": [],
            "context": {
                "log_class": {
                    "logclass0": "",
                    "logclass1": "",
                    "logclass2": "",
                    "logclass3": "on",
                    "logclass4": "",
                    "logclass5": "",
                    "logclass6": "",
                },
                "hostregex": {"host_regex": ""},
                "serviceregex": {"service_regex": ""},
                "log_plugin_output": {"log_plugin_output": ""},
                "logtime": {"logtime_from": "24", "logtime_from_range": "3600"},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # All events of a Host
        "mobile_hostsvcevents": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidebutton": False,
            "public": True,
            "topic": "overview",
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "hidden": True,
            "icon": "history",
            "datasource": "log_events",
            "group_painters": [ColumnSpec(name="log_date")],
            "layout": "mobilelist",
            "name": "mobile_hostsvcevents",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="log_icon"),
                ColumnSpec(name="log_time"),
                ColumnSpec(name="log_type"),
                ColumnSpec(name="host"),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_svcevents"),
                ),
                ColumnSpec(name="log_state_type"),
                ColumnSpec(name="log_plugin_output"),
            ],
            "sorters": [
                SorterSpec(sorter="log_time", negate=False),
                SorterSpec(sorter="log_lineno", negate=False),
            ],
            "title": _l("Events of host & services"),
            "owner": UserId.builtin(),
            "single_infos": ["host"],
            "context": {
                "site": {},
                "logtime": {"logtime_from": "7", "logtime_from_range": "86400"},
                "log_state": {},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # All events of one service
        "mobile_svcevents": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidebutton": False,
            "public": True,
            "topic": "overview",
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "hidden": True,
            "icon": "history",
            "datasource": "log_events",
            "group_painters": [ColumnSpec(name="log_date")],
            "layout": "mobilelist",
            "name": "mobile_svcevents",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="log_icon"),
                ColumnSpec(name="log_time"),
                ColumnSpec(name="log_type"),
                ColumnSpec(name="log_state_type"),
                ColumnSpec(name="log_plugin_output"),
            ],
            "sorters": [
                SorterSpec(sorter="log_time", negate=False),
                SorterSpec(sorter="log_lineno", negate=False),
            ],
            "title": _l("Events of service"),
            "owner": UserId.builtin(),
            "single_infos": ["service", "host"],
            "context": {
                "site": {},
                "logtime": {"logtime_from": "7", "logtime_from_range": "86400"},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # All Notfications of a contact
        "mobile_contactnotifications": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidebutton": False,
            "public": True,
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "hidden": True,
            "icon": "notifications",
            "topic": "history",
            "datasource": "log",
            "group_painters": [ColumnSpec(name="log_date")],
            "layout": "mobilelist",
            "name": "mobile_contactnotifications",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="log_time"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_hostsvcnotifications"),
                ),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_svcnotifications"),
                ),
                ColumnSpec(name="log_type"),
                ColumnSpec(name="log_state"),
                ColumnSpec(name="log_plugin_output"),
            ],
            "sorters": [
                SorterSpec(sorter="log_time", negate=False),
                SorterSpec(sorter="log_lineno", negate=False),
            ],
            "title": _l("Notifications of contact"),
            "owner": UserId.builtin(),
            "single_infos": ["contact"],
            "context": {
                "log_class": {
                    "logclass0": "",
                    "logclass1": "",
                    "logclass2": "",
                    "logclass3": "on",
                    "logclass4": "",
                    "logclass5": "",
                    "logclass6": "",
                },
                "host": {"host": ""},
                "serviceregex": {"service_regex": ""},
                "log_plugin_output": {"log_plugin_output": ""},
                "logtime": {"logtime_from": "7", "logtime_from_range": "86400"},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # All Notfications of Host
        "mobile_hostsvcnotifications": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidebutton": False,
            "public": True,
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "hidden": True,
            "icon": "notifications",
            "topic": "history",
            "datasource": "log",
            "group_painters": [ColumnSpec(name="log_date")],
            "layout": "mobilelist",
            "name": "mobile_hostsvcnotifications",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="log_time"),
                ColumnSpec(name="log_contact_name"),
                ColumnSpec(name="log_type"),
                ColumnSpec(
                    name="host",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_hostsvcnotifications"),
                ),
                ColumnSpec(
                    name="service_description",
                    link_spec=VisualLinkSpec(type_name="views", name="mobile_svcnotifications"),
                ),
                ColumnSpec(name="log_state"),
                ColumnSpec(name="log_plugin_output"),
            ],
            "sorters": [
                SorterSpec(sorter="log_time", negate=False),
                SorterSpec(sorter="log_lineno", negate=False),
            ],
            "title": _l("Notifications of host & services"),
            "owner": UserId.builtin(),
            "single_infos": ["host"],
            "context": {
                "site": {},
                "log_class": {
                    "logclass0": "",
                    "logclass1": "",
                    "logclass2": "",
                    "logclass3": "on",
                    "logclass4": "",
                    "logclass5": "",
                    "logclass6": "",
                },
                "serviceregex": {"service_regex": ""},
                "log_plugin_output": {"log_plugin_output": ""},
                "logtime": {"logtime_from": "7", "logtime_from_range": "86400"},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
        # All Notfications of a service
        "mobile_svcnotifications": {
            "mobile": True,
            "browser_reload": 0,
            "column_headers": "pergroup",
            "description": _l("This view is used by the mobile GUI"),
            "hidebutton": False,
            "public": True,
            "user_sortable": False,
            "play_sounds": False,
            "mustsearch": False,
            "hidden": True,
            "icon": "notifications",
            "topic": "history",
            "datasource": "log",
            "group_painters": [ColumnSpec(name="log_date")],
            "layout": "mobilelist",
            "name": "mobile_svcnotifications",
            "num_columns": 2,
            "painters": [
                ColumnSpec(name="log_time"),
                ColumnSpec(name="log_contact_name"),
                ColumnSpec(name="host"),
                ColumnSpec(name="log_state"),
                ColumnSpec(name="log_plugin_output"),
            ],
            "sorters": [
                SorterSpec(sorter="log_time", negate=False),
                SorterSpec(sorter="log_lineno", negate=False),
            ],
            "title": _l("Service notifications"),
            "owner": UserId.builtin(),
            "single_infos": ["service", "host"],
            "context": {
                "site": {},
                "log_class": {
                    "logclass0": "",
                    "logclass1": "",
                    "logclass2": "",
                    "logclass3": "on",
                    "logclass4": "",
                    "logclass5": "",
                    "logclass6": "",
                },
                "log_plugin_output": {"log_plugin_output": ""},
                "logtime": {"logtime_from": "7", "logtime_from_range": "86400"},
            },
            "link_from": {},
            "add_context_to_title": True,
            "sort_index": 99,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
        },
    }
)

# .
#   .--Layouts-------------------------------------------------------------.
#   |                _                            _                        |
#   |               | |    __ _ _   _  ___  _   _| |_ ___                  |
#   |               | |   / _` | | | |/ _ \| | | | __/ __|                 |
#   |               | |__| (_| | |_| | (_) | |_| | |_\__ \                 |
#   |               |_____\__,_|\__, |\___/ \__,_|\__|___/                 |
#   |                           |___/                                      |
#   +----------------------------------------------------------------------+
#   | Display-Layouts for the views used by mobile. There are two layouts: |
#   | one for a list of items, one for a single dataset.                   |
#   '----------------------------------------------------------------------'


def render_mobile_table(
    rows: Rows,
    view: ViewSpec,
    group_cells: Sequence[Cell],
    cells: Sequence[Cell],
    num_columns: int,
    show_checkboxes: bool,
) -> None:
    if not is_mobile(request, response):
        html.show_error(_("This view can only be used in mobile mode."))
        return

    # Force relative timestamp always. This saves space.
    painter_options = PainterOptions.get_instance()
    painter_options.set("ts_format", "rel")

    odd = "odd"
    html.open_table(class_="mobile data")

    # Paint header
    if view.get("column_headers") != "off":
        html.open_tr()
        n = 0
        for cell in cells:
            cell.paint_as_header()
        html.close_tr()

    link_renderer = partial(render_link_to_view, request=request)
    # Paint data rows
    for row in rows:
        odd = "even" if odd == "odd" else "odd"
        html.open_tr(class_="%s0" % odd)
        for n, cell in enumerate(cells):
            if n > 0 and n % num_columns == 0:
                html.close_tr()
                html.open_tr(class_="%s0" % odd)

            if n == len(cells) - 1 and n % num_columns != (num_columns - 1):
                colspan = num_columns - (n % num_columns)
            else:
                colspan = None

            cell.paint(row, link_renderer, user=user, colspan=colspan)
        html.close_tr()
    html.close_table()
    html.javascript('$("table.mobile a").attr("data-ajax", "false");')


class LayoutMobileTable(Layout):
    @property
    @override
    def ident(self) -> str:
        return "mobiletable"

    @property
    @override
    def title(self) -> str:
        return _("Mobile: Table")

    @property
    @override
    def can_display_checkboxes(self) -> bool:
        return False

    @override
    def render(
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        render_mobile_table(rows, view, group_cells, cells, num_columns, show_checkboxes)


def render_mobile_list(
    rows: Rows,
    view: ViewSpec,
    group_cells: Sequence[Cell],
    cells: Sequence[Cell],
    num_columns: int,
    show_checkboxes: bool,
) -> None:
    if not is_mobile(request, response):
        html.show_error(_("This view can only be used in mobile mode."))
        return

    # Force relative timestamp always. This saves space.
    painter_options = PainterOptions.get_instance()
    painter_options.set("ts_format", "rel")

    html.open_ul(class_="mobilelist", **{"data-role": "listview"})

    link_renderer = partial(render_link_to_view, request=request)
    # Paint data rows
    for row in rows:
        html.open_li()
        rendered_cells = [cell.render(row, link_renderer, user) for cell in cells]
        if rendered_cells:  # First cell (assumedly state) is left
            rendered_class, rendered_content = rendered_cells[0]
            assert isinstance(rendered_content, str | HTML)
            html.p(rendered_content, class_=["ui-li-aside", "ui-li-desc", rendered_class])

            if len(rendered_cells) > 1:
                content = HTML.without_escaping(" &middot; ").join(
                    [
                        rendered_cell[1]
                        for rendered_cell in rendered_cells[1 : num_columns + 1]
                        if isinstance(rendered_cell[1], str | HTML)
                    ]
                )
                html.h3(content)

                for rendered_cell, cell in zip(
                    rendered_cells[num_columns + 1 :], cells[num_columns + 1 :]
                ):
                    rendered_class, rendered_content = rendered_cell
                    assert isinstance(rendered_content, str | HTML)
                    html.open_p(class_="ui-li-desc")
                    cell.paint_as_header()
                    html.write_text_permissive(": ")
                    html.span(rendered_content, class_=rendered_class)
                    html.close_p()

        html.close_li()
    html.close_ul()
    html.javascript('$("ul.mobilelist a").attr("data-ajax", "false");')


class LayoutMobileList(Layout):
    @property
    @override
    def ident(self) -> str:
        return "mobilelist"

    @property
    @override
    def title(self) -> str:
        return _("Mobile: List")

    @property
    @override
    def can_display_checkboxes(self) -> bool:
        return False

    @override
    def render(
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        render_mobile_list(rows, view, group_cells, cells, num_columns, show_checkboxes)


def render_mobile_dataset(
    rows: Rows,
    view: ViewSpec,
    group_cells: Sequence[Cell],
    cells: Sequence[Cell],
    num_columns: int,
    show_checkboxes: bool,
) -> None:
    if not is_mobile(request, response):
        html.show_error(_("This view can only be used in mobile mode."))
        return

    painter_options = PainterOptions.get_instance()
    painter_options.set("ts_format", "both")

    link_renderer = partial(render_link_to_view, request=request)
    for row in rows:
        html.open_table(class_="dataset")
        for cell in cells:
            _tdclass, content = cell.render(row, link_renderer, user)
            if not content:
                continue  # Omit empty cells

            html.open_tr(class_="header")
            html.th(cell.title())
            html.close_tr()

            html.open_tr(class_="data")
            cell.paint(row, link_renderer, user=user)
            html.close_tr()

        html.close_table()
    html.javascript(
        '$("table.dataset > tbody > tr.data > td").addClass("ui-shadow").not(".state").addClass("nonstatus");\n'
        '$("table.dataset > tbody > tr.data a").attr("data-ajax", "false");\n'
    )


class LayoutMobileDataset(Layout):
    @property
    @override
    def ident(self) -> str:
        return "mobiledataset"

    @property
    @override
    def title(self) -> str:
        return _("Mobile: Dataset")

    @property
    @override
    def can_display_checkboxes(self) -> bool:
        return False

    @override
    def render(
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        render_mobile_dataset(rows, view, group_cells, cells, num_columns, show_checkboxes)
