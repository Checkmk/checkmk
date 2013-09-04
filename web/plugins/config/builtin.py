#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
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
profile                = False
users                  = []
admin_users            = []
guest_users            = []
default_user_role      = "user"
save_user_access_times = False
user_online_maxage     = 30 # seconds

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
view_option_columns   = [ 1, 2, 3, 4, 5, 6, 8 ]

# MISC
doculink_urlformat = "http://mathias-kettner.de/checkmk_%s.html";


#   ____          _                    _     _       _
#  / ___|   _ ___| |_ ___  _ __ ___   | |   (_)_ __ | | _____
# | |  | | | / __| __/ _ \| '_ ` _ \  | |   | | '_ \| |/ / __|
# | |__| |_| \__ \ || (_) | | | | | | | |___| | | | |   <\__ \
#  \____\__,_|___/\__\___/|_| |_| |_| |_____|_|_| |_|_|\_\___/
#

custom_links = {}

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

# Default authentication type. Can be changed to e.g. "cookie" for
# using the cookie auth
auth_type = 'basic'

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
multisite_draw_ruleicon = False

# Default downtime configuration
adhoc_downtime = {}

# Display dashboard date
pagetitle_date_format = None

# Value of the host_staleness/service_staleness field to make hosts/services
# appear in a stale state
staleness_threshold = 1.5

#     _   _               ____  ____
#    | | | |___  ___ _ __|  _ \| __ )
#    | | | / __|/ _ \ '__| | | |  _ \
#    | |_| \__ \  __/ |  | |_| | |_) |
#     \___/|___/\___|_|  |____/|____/
#

user_connectors       = ['htpasswd']
userdb_automatic_sync = [ 'wato_users', 'page' ]
ldap_connection       = {}
ldap_userspec         = {}
ldap_groupspec        = {}
ldap_active_plugins   = {'email': {}, 'alias': {}, 'auth_expire': {}}
ldap_cache_livetime   = 300
ldap_debug_log        = None
default_user_profile  = {
    'roles': ['user'],
}
lock_on_logon_failures = False
