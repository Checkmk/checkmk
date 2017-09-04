#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

#    ____       _
#   |  _ \ ___ | | ___  ___
#   | |_) / _ \| |/ _ \/ __|
#   |  _ < (_) | |  __/\__ \
#   |_| \_\___/|_|\___||___/
#
roles = {} # User supplied roles

# define default values for all settings
debug                  = False
screenshotmode         = False
profile                = False
users                  = []
admin_users            = ["omdadmin", "cmkadmin"]
guest_users            = []
default_user_role      = "user"
save_user_access_times = False
user_online_maxage     = 30 # seconds

log_levels = {
    "cmk.web"                : 30,
    "cmk.web.ldap"           : 30,
    "cmk.web.auth"           : 30,
    "cmk.web.bi.compilation" : 30,
}

# New style, used by WATO
multisite_users = {}

#    ____  _     _      _
#   / ___|(_) __| | ___| |__   __ _ _ __
#   \___ \| |/ _` |/ _ \ '_ \ / _` | '__|
#    ___) | | (_| |  __/ |_) | (_| | |
#   |____/|_|\__,_|\___|_.__/ \__,_|_|
#

sidebar = [
    ('tactical_overview', 'open'),
    ('search',            'open'),
    ('views',             'open'),
    ('reports',           'closed'), # does not harm if not available
    ('bookmarks',         'open'),
    ('admin',             'open'),
    ('master_control',    'closed')
]

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
quicksearch_search_order = [("h", "continue"), ("al", "continue"), ("ad", "continue"), ("s", "continue")]

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
    ( "down",     "down.wav" ),
    ( "critical", "critical.wav" ),
    ( "unknown",  "unknown.wav" ),
    ( "warning",  "warning.wav" ),
    # ( None,       "ok.wav" ),
]


#   __     ___                             _   _
#   \ \   / (_) _____      __   ___  _ __ | |_(_) ___  _ __  ___
#    \ \ / /| |/ _ \ \ /\ / /  / _ \| '_ \| __| |/ _ \| '_ \/ __|
#     \ V / | |  __/\ V  V /  | (_) | |_) | |_| | (_) | | | \__ \
#      \_/  |_|\___| \_/\_/    \___/| .__/ \__|_|\___/|_| |_|___/
#                                   |_|

view_option_refreshes = [ 30, 60, 90, 0 ]
view_option_columns   = [ 1, 2, 3, 4, 5, 6, 8, 10, 12 ]

# MISC
doculink_urlformat = "http://mathias-kettner.com/checkmk_%s.html"

view_action_defaults = {
    "ack_sticky"     : True,
    "ack_notify"     : True,
    "ack_persistent" : False,
}


#   ____          _                    _     _       _
#  / ___|   _ ___| |_ ___  _ __ ___   | |   (_)_ __ | | _____
# | |  | | | / __| __/ _ \| '_ ` _ \  | |   | | '_ \| |/ / __|
# | |__| |_| \__ \ || (_) | | | | | | | |___| | | | |   <\__ \
#  \____\__,_|___/\__\___/|_| |_| |_| |_____|_|_| |_|_|\_\___/
#

custom_links = {}

# Links for everyone
custom_links['guest'] = [
  ( "Classical Nagios GUI", "../nagios/", "icon_home.png" ),
  ( "Addons", True, [
        ( "NagVis",     "../nagvis/", "icon_nagvis.png" ),
  ]),
]

# The members of the role 'user' get the same links as the guests
# but some in addition
custom_links['user'] = custom_links['guest'] + [
  ( "Open Source Components", False, [
        ( "Check_MK",      "http://mathias-kettner.com/check_mk.html", None, "_blank"),
        ( "Nagios",        "http://www.nagios.org/", None, "_blank"),
        ( "PNP4Nagios",    "http://pnp4nagios.org/", None, "_blank"),
        ( "NagVis",        "http://nagvis.org/", None, "_blank"),
        ( "RRDTool",       "http://oss.oetiker.ch/rrdtool/", None, "_blank"),
   ])
]

# The admins yet get further links
custom_links['admin'] = custom_links['user'] + [
  ( "Support", False, [
      ( "Mathias Kettner",            "http://mathias-kettner.com/" ),
      ( "Check_MK Mailinglists",      "http://mathias-kettner.com/check_mk_lists.html" ),
      ( "Check_MK Exchange",          "http://exchange.check-mk.org/", None, "_blank" ),
      ( "Monitoring Portal (German)", "http://monitoring-portal.org", None, "_blank"),
  ])
]

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
service_view_grouping = []

# Custom user stylesheet to load (resides in htdocs/)
custom_style_sheet = None

# URL for start page in main frame (welcome page)
start_url = "dashboard.py"

# Page heading for main frame set
page_heading = "Check_MK %s"

# Timeout for rescheduling of host- and servicechecks
reschedule_timeout = 10.0

# Number of columsn in "Filter" form
filter_columns = 2

# Default language for l10n
default_language = None

# Hide these languages from user selection
hide_languages = []

# Default timestamp format to be used in multisite
default_ts_format = 'mixed'

# Show only most used buttons, set to None if you want
# always all buttons to be shown
context_buttons_to_show = 5

# Buffering of HTML output stream
buffered_http_stream = True

# Maximum livetime of unmodified selections
selection_livetime  = 3600

# Configure HTTP header to read usernames from
auth_by_http_header = False

# Number of rows to display by default in tables rendered with
# the table.py module
table_row_limit = 100

# Add an icon pointing to the WATO rule to each service
multisite_draw_ruleicon = True

# Default downtime configuration
adhoc_downtime = {}

# Display dashboard date
pagetitle_date_format = None

# Value of the host_staleness/service_staleness field to make hosts/services
# appear in a stale state
staleness_threshold = 1.5

# Escape HTML in plugin output / log messages
escape_plugin_output = True

# Virtual host trees for the "Virtual Host Trees" snapin
virtual_host_trees = []

# Fall back to PNP4Nagios as graphing GUI even on CEE
force_pnp_graphing = False

# Target email address for "Crashed Check" page
crash_report_target = "feedback@check-mk.org"

# GUI Tests (see cmk-guitest)
guitests_enabled = False

# Bulk discovery default options
bulk_discovery_default_settings = {
    "mode"           : "new",
    "selection"      : (True, False, False, False),
    "performance"    : (True, True, 10),
    "error_handling" : True,
}

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
user_connections = []

default_user_profile  = {
    'contactgroups': [],
    'roles': ['user'],
}
lock_on_logon_failures = False
user_idle_timeout      = None
single_user_session    = None
password_policy        = {}

user_localizations = {
    u'Agent type':                          { "de": u"Art des Agenten", },
    u'Business critical':                   { "de": u"Geschäftskritisch", },
    u'Check_MK Agent (Server)':             { "de": u"Check_MK Agent (Server)", },
    u'Criticality':                         { "de": u"Kritikalität", },
    u'DMZ (low latency, secure access)':    { "de": u"DMZ (geringe Latenz, hohe Sicherheit", },
    u'Do not monitor this host':            { "de": u"Diesen Host nicht überwachen", },
    u'Dual: Check_MK Agent + SNMP':         { "de": u"Dual: Check_MK Agent + SNMP", },
    u'Legacy SNMP device (using V1)':       { "de": u"Alte SNMP-Geräte (mit Version 1)", },
    u'Local network (low latency)':         { "de": u"Lokales Netzwerk (geringe Latenz)", },
    u'Networking Segment':                  { "de": u"Netzwerksegment", },
    u'No Agent':                            { "de": u"Kein Agent", },
    u'Productive system':                   { "de": u"Produktivsystem", },
    u'Test system':                         { "de": u"Testsystem", },
    u'WAN (high latency)':                  { "de": u"WAN (hohe Latenz)", },
    u'monitor via Check_MK Agent':          { "de": u"Überwachung via Check_MK Agent", },
    u'monitor via SNMP':                    { "de": u"Überwachung via SNMP", },
    u'SNMP (Networking device, Appliance)': { "de": u"SNMP (Netzwerkgerät, Appliance)", },
}

# Contains user specified icons and actions for hosts and services
user_icons_and_actions = {}

user_downtime_timeranges = [
            {'title': _("2 hours"),    'end': 2 * 60 * 60},
            {'title': _("Today"),      'end': 'next_day'},
            {'title': _("This week"),  'end': 'next_week'},
            {'title': _("This month"), 'end': 'next_month'},
            {'title': _("This year"),  'end': 'next_year'},
        ]

# Override toplevel and sort_index settings of builtin icons
builtin_icon_visibility = {}

# Name of the hostgroup to filter the network topology view by default
topology_default_filter_group = None

trusted_certificate_authorities = {
    "use_system_wide_cas": True,
    "trusted_cas": [],
}
