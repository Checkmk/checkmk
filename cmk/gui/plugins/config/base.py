#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Default configuration settings for the Check_MK GUI"""

from typing import (  # pylint: disable=unused-import
    Dict as _Dict, List as _List, Tuple as _Tuple, Any as _Any,
)

#.
#   .--Generic-------------------------------------------------------------.
#   |                   ____                      _                        |
#   |                  / ___| ___ _ __   ___ _ __(_) ___                   |
#   |                 | |  _ / _ \ '_ \ / _ \ '__| |/ __|                  |
#   |                 | |_| |  __/ | | |  __/ |  | | (__                   |
#   |                  \____|\___|_| |_|\___|_|  |_|\___|                  |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# User supplied roles
roles = {}  # type: _Dict

# define default values for all settings
debug = False
screenshotmode = False
profile = False
users = []  # type: _List
admin_users = ["omdadmin", "cmkadmin"]
guest_users = []  # type: _List
default_user_role = "user"
save_user_access_times = False
user_online_maxage = 30  # seconds

log_levels = {
    "cmk.web": 30,
    "cmk.web.ldap": 30,
    "cmk.web.auth": 30,
    "cmk.web.bi.compilation": 30,
    "cmk.web.automations": 30,
    "cmk.web.background-job": 30,
}

multisite_users = {}  # type: _Dict
multisite_hostgroups = {}  # type: _Dict
multisite_servicegroups = {}  # type: _Dict
multisite_contactgroups = {}  # type: _Dict

#    ____  _     _      _
#   / ___|(_) __| | ___| |__   __ _ _ __
#   \___ \| |/ _` |/ _ \ '_ \ / _` | '__|
#    ___) | | (_| |  __/ |_) | (_| | |
#   |____/|_|\__,_|\___|_.__/ \__,_|_|
#

sidebar = [('tactical_overview', 'open'), ('search', 'open'), ('views', 'open'), ('admin', 'open'),
           ('bookmarks', 'open'), ('master_control', 'closed')]

# Interval of snapin updates in seconds
sidebar_update_interval = 30.0

# It is possible (but ugly) to enable a scrollbar in the sidebar
sidebar_show_scrollbar = False

# Enable regular checking for popup notifications
sidebar_notify_interval = None

sidebar_show_version_in_sidebar = True

# Maximum number of results to show in quicksearch dropdown
quicksearch_dropdown_limit = 80

# Quicksearch search order
quicksearch_search_order = [("h", "continue"), ("al", "continue"), ("ad", "continue"),
                            ("s", "continue")]

failed_notification_horizon = 7 * 60 * 60 * 24

#    _     _           _ _
#   | |   (_)_ __ ___ (_) |_ ___
#   | |   | | '_ ` _ \| | __/ __|
#   | |___| | | | | | | | |_\__ \
#   |_____|_|_| |_| |_|_|\__|___/
#

soft_query_limit = 1000
hard_query_limit = 5000

#    ____                        _
#   / ___|  ___  _   _ _ __   __| |___
#   \___ \ / _ \| | | | '_ \ / _` / __|
#    ___) | (_) | |_| | | | | (_| \__ \
#   |____/ \___/ \__,_|_| |_|\__,_|___/
#

sound_url = "sounds/"
enable_sounds = False
sounds = [
    ("down", "down.wav"),
    ("critical", "critical.wav"),
    ("unknown", "unknown.wav"),
    ("warning", "warning.wav"),
    # ( None,       "ok.wav" ),
]

#   __     ___                             _   _
#   \ \   / (_) _____      __   ___  _ __ | |_(_) ___  _ __  ___
#    \ \ / /| |/ _ \ \ /\ / /  / _ \| '_ \| __| |/ _ \| '_ \/ __|
#     \ V / | |  __/\ V  V /  | (_) | |_) | |_| | (_) | | | \__ \
#      \_/  |_|\___| \_/\_/    \___/| .__/ \__|_|\___/|_| |_|___/
#                                   |_|

view_option_refreshes = [30, 60, 90, 0]
view_option_columns = [1, 2, 3, 4, 5, 6, 8, 10, 12]

# MISC
doculink_urlformat = "https://checkmk.com/checkmk_%s.html"

view_action_defaults = {
    "ack_sticky": True,
    "ack_notify": True,
    "ack_persistent": False,
}

#   ____          _                    _     _       _
#  / ___|   _ ___| |_ ___  _ __ ___   | |   (_)_ __ | | _____
# | |  | | | / __| __/ _ \| '_ ` _ \  | |   | | '_ \| |/ / __|
# | |__| |_| \__ \ || (_) | | | | | | | |___| | | | |   <\__ \
#  \____\__,_|___/\__\___/|_| |_| |_| |_____|_|_| |_|_|\_\___/
#

# TODO: Improve type below, see cmk.gui.plugins.sidebar.custom_links
custom_links = {}  # type: _Dict[str, _List[_Tuple]]

# Links for everyone
custom_links['guest'] = [
    ("Addons", True, [
        ("NagVis", "../nagvis/", "icon_nagvis.png"),
    ]),
]

# The members of the role 'user' get the same links as the guests
# but some in addition
custom_links['user'] = custom_links['guest'] + [("Open Source Components", False, [
    ("CheckMK", "https://checkmk.com", None, "_blank"),
    ("Nagios", "https://www.nagios.org/", None, "_blank"),
    ("NagVis", "https://nagvis.org/", None, "_blank"),
    ("RRDTool", "https://oss.oetiker.ch/rrdtool/", None, "_blank"),
])]

# The admins yet get further links
custom_links['admin'] = custom_links['user'] + [("Support", False, [
    ("CheckMK", "https://checkmk.com/", None, "_blank"),
    ("CheckMK Mailinglists", "https://checkmk.com/community.php", None, "_blank"),
    ("CheckMK Exchange", "https://checkmk.com/check_mk-exchange.php", None, "_blank"),
])]

#  __     __         _
#  \ \   / /_ _ _ __(_) ___  _   _ ___
#   \ \ / / _` | '__| |/ _ \| | | / __|
#    \ V / (_| | |  | | (_) | |_| \__ \
#     \_/ \__,_|_|  |_|\___/ \__,_|___/
#

debug_livestatus_queries = False

# Show livestatus errors in multi site setup if some sites are
# not reachable.
show_livestatus_errors = True

# Whether the livestatu proxy daemon is available
liveproxyd_enabled = False

# Set this to a list in order to globally control which views are
# being displayed in the sidebar snapin "Views"
visible_views = None

# Set this list in order to actively hide certain views
hidden_views = None

# Patterns to group services in table views together
service_view_grouping = []  # type: _List

# Custom user stylesheet to load (resides in htdocs/)
custom_style_sheet = None

# UI theme to use
ui_theme = "classic"

# URL for start page in main frame (welcome page)
start_url = "dashboard.py"

# Page heading for main frame set
page_heading = "Checkmk %s"

login_screen = {}  # type: _Dict

# Timeout for rescheduling of host- and servicechecks
reschedule_timeout = 10.0

# Number of columsn in "Filter" form
filter_columns = 2

# Default language for l10n
default_language = None

# Hide these languages from user selection
hide_languages = []  # type: _List

# Default timestamp format to be used in multisite
default_ts_format = 'mixed'

# Show only most used buttons, set to None if you want
# always all buttons to be shown
context_buttons_to_show = 5

# Maximum livetime of unmodified selections
selection_livetime = 3600

# Configure HTTP header to read usernames from
auth_by_http_header = False

# Number of rows to display by default in tables rendered with
# the table.py module
table_row_limit = 100

# Add an icon pointing to the WATO rule to each service
multisite_draw_ruleicon = True

# Default downtime configuration
adhoc_downtime = {}  # type: _Dict

# Display dashboard date
pagetitle_date_format = None

# Value of the host_staleness/service_staleness field to make hosts/services
# appear in a stale state
staleness_threshold = 1.5

# Escape HTML in plugin output / log messages
escape_plugin_output = True

# Virtual host trees for the "Virtual Host Trees" snapin
virtual_host_trees = []  # type: _List

# Target URL for sending crash reports to
crash_report_url = "https://crash.checkmk.com"
# Target email address for "Crashed Check" page
crash_report_target = "feedback@checkmk.com"

# GUI Tests (see cmk-guitest)
guitests_enabled = False

# Bulk discovery default options
bulk_discovery_default_settings = {
    "mode": "new",
    "selection": (True, False, False, False),
    "performance": (True, True, 10),
    "error_handling": True,
}

use_siteicons = False

graph_timeranges = [
    {
        'title': "The last 4 hours",
        "duration": 4 * 60 * 60
    },
    {
        'title': "The last 25 hours",
        "duration": 25 * 60 * 60
    },
    {
        'title': "The last 8 days",
        "duration": 8 * 24 * 60 * 60
    },
    {
        'title': "The last 35 days",
        "duration": 35 * 24 * 60 * 60
    },
    {
        'title': "The last 400 days",
        "duration": 400 * 24 * 60 * 60
    },
]  # type: _List[_Dict[str, _Any]]

#     _   _               ____  ____
#    | | | |___  ___ _ __|  _ \| __ )
#    | | | / __|/ _ \ '__| | | |  _ \
#    | |_| \__ \  __/ |  | |_| | |_) |
#     \___/|___/\___|_|  |____/|____/
#

# This option can not be configured through WATO anymore. Config has been
# moved to the sites configuration. This might have been configured in master/remote
# in previous versions and is set on remote sites during WATO synchronization.
userdb_automatic_sync = "master"

# Holds dicts defining user connector instances and their properties
user_connections = []  # type: _List

default_user_profile = {
    'contactgroups': [],
    'roles': ['user'],
    'force_authuser': False,
}  # type: _Dict[str, _Any]
lock_on_logon_failures = False
user_idle_timeout = None
single_user_session = None
password_policy = {}  # type: _Dict

user_localizations = {
    u'Agent type': {
        "de": u"Art des Agenten",
    },
    u'Business critical': {
        "de": u"Geschäftskritisch",
    },
    u'Check_MK Agent (Server)': {
        "de": u"Check_MK Agent (Server)",
    },
    u'Criticality': {
        "de": u"Kritikalität",
    },
    u'DMZ (low latency, secure access)': {
        "de": u"DMZ (geringe Latenz, hohe Sicherheit",
    },
    u'Do not monitor this host': {
        "de": u"Diesen Host nicht überwachen",
    },
    u'Dual: Check_MK Agent + SNMP': {
        "de": u"Dual: Check_MK Agent + SNMP",
    },
    u'Legacy SNMP device (using V1)': {
        "de": u"Alte SNMP-Geräte (mit Version 1)",
    },
    u'Local network (low latency)': {
        "de": u"Lokales Netzwerk (geringe Latenz)",
    },
    u'Networking Segment': {
        "de": u"Netzwerksegment",
    },
    u'No Agent': {
        "de": u"Kein Agent",
    },
    u'Productive system': {
        "de": u"Produktivsystem",
    },
    u'Test system': {
        "de": u"Testsystem",
    },
    u'WAN (high latency)': {
        "de": u"WAN (hohe Latenz)",
    },
    u'monitor via Check_MK Agent': {
        "de": u"Überwachung via Check_MK Agent",
    },
    u'monitor via SNMP': {
        "de": u"Überwachung via SNMP",
    },
    u'SNMP (Networking device, Appliance)': {
        "de": u"SNMP (Netzwerkgerät, Appliance)",
    },
}

# Contains user specified icons and actions for hosts and services
user_icons_and_actions = {}  # type: _Dict

# Defintions of custom attributes to be used for services
custom_service_attributes = {}  # type: _Dict

user_downtime_timeranges = [
    {
        'title': "2 hours",
        'end': 2 * 60 * 60
    },
    {
        'title': "Today",
        'end': 'next_day'
    },
    {
        'title': "This week",
        'end': 'next_week'
    },
    {
        'title': "This month",
        'end': 'next_month'
    },
    {
        'title': "This year",
        'end': 'next_year'
    },
]  # type: _List[_Dict[str, _Any]]

# Override toplevel and sort_index settings of builtin icons
builtin_icon_visibility = {}  # type: _Dict

# Name of the hostgroup to filter the network topology view by default
topology_default_filter_group = None

trusted_certificate_authorities = {
    "use_system_wide_cas": True,
    "trusted_cas": [],
}

#.
#   .--EC------------------------------------------------------------------.
#   |                             _____ ____                               |
#   |                            | ____/ ___|                              |
#   |                            |  _|| |                                  |
#   |                            | |__| |___                               |
#   |                            |_____\____|                              |
#   |                                                                      |
#   '----------------------------------------------------------------------'

mkeventd_enabled = True
mkeventd_pprint_rules = False
mkeventd_notify_contactgroup = ''
mkeventd_notify_facility = 16
mkeventd_notify_remotehost = None
mkeventd_connect_timeout = 10
log_level = 0
log_rulehits = False
rule_optimizer = True

mkeventd_service_levels = [
    (0, "(no Service level)"),
    (10, "Silver"),
    (20, "Gold"),
    (30, "Platinum"),
]

#.
#   .--WATO----------------------------------------------------------------.
#   |                     __        ___  _____ ___                         |
#   |                     \ \      / / \|_   _/ _ \                        |
#   |                      \ \ /\ / / _ \ | || | | |                       |
#   |                       \ V  V / ___ \| || |_| |                       |
#   |                        \_/\_/_/   \_\_| \___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Pre 1.6 tag configuration variables
wato_host_tags = []  # type: _List
wato_aux_tags = []  # type: _List
# Tag configuration variable since 1.6
wato_tags = {
    "tag_groups": [],
    "aux_tags": [],
}  # type: _Dict[str, _List]

wato_enabled = True
wato_hide_filenames = True
wato_hide_hosttags = False
wato_upload_insecure_snapshots = False
wato_hide_varnames = True
wato_hide_help_in_lists = True
wato_max_snapshots = 50
wato_num_hostspecs = 12
wato_num_itemspecs = 15
wato_activation_method = 'restart'
wato_write_nagvis_auth = False
wato_use_git = False
wato_hidden_users = []  # type: _List
wato_user_attrs = []  # type: _List
wato_host_attrs = []  # type: _List
wato_legacy_eval = False
wato_read_only = {}  # type: _Dict
wato_hide_folders_without_read_permissions = False
wato_pprint_config = False
wato_icon_categories = [
    ("logos", u"Logos"),
    ("parts", u"Parts"),
    ("misc", u"Misc"),
]

#.
#   .--BI------------------------------------------------------------------.
#   |                              ____ ___                                |
#   |                             | __ )_ _|                               |
#   |                             |  _ \| |                                |
#   |                             | |_) | |                                |
#   |                             |____/___|                               |
#   |                                                                      |
#   '----------------------------------------------------------------------'

aggregation_rules = {}  # type: _Dict
aggregations = []  # type: _List
host_aggregations = []  # type: _List
bi_packs = {}  # type: _Dict
bi_precompile_on_demand = True
bi_use_legacy_compilation = False

default_bi_layout = {"node_style": "builtin_hierarchy", "line_style": "straight"}
bi_layouts = {"templates": {}, "aggregations": {}}  # type: _Dict[str, _Dict]

# Deprecated. Kept for compatibility.
bi_compile_log = None
