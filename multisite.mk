# Confguration for Check_MK Multisite

# Users with unrestricted permissions
admin_users = [ "nagiosadmin" ]

# Users seeing all data but cannot do any action
# guest_users = [ "guest" ]

# A lists of all normal operational users allowed to use
# Multisite. If this variable is not set, then everybody with a correct
# HTTP login may use Multisite and gets the role "user"
# users       = [ "meier", "huber", "mueller" ]

# Users not explicitely being listed in admin_users or guest_users
# get the role "user" if they have a valid login. You can change this
# to "guest", "admin" or None by setting the following variable:
# default_user_role = "guest"

# Sites to connect to. If this variable is unset, a single
# connection to the local host is done.
sites = {
   # connect to local Nagios
   "wato" : {
        "alias" : "Munich"
   },
}
#
#   # connect to remote site (e.g. local OMD site 'paris')
#   "paris": {
#        "alias":          "Paris",
#        "socket":         "tcp:127.0.0.1:6557",
#        "url_prefix":     "/paris/",
#    },
#
#   # connect to remote site (site on remote host)
#   "rome": {
#        "alias":          "Rome",
#        "socket":         "tcp:10.0.0.2:6557",
#        "url_prefix":     "http://10.0.0.2/rome/",
#    },
#}

# 
# NagVis
#
# The NagVis-Snapin needs to know the URL to nagvis.
# This is not always /nagvis/ - especially not for OMD
nagvis_base_url = '/nagvis'


# Restrict number of datasets queries via Livestatus.
# This prevents you from consuming too much ressources
# in case of insensible queries.
# soft_query_limit = 1000
# hard_query_limit = 5000

# Views allow to play alarm sounds according to the
# "worst" state of the show items. Configure here
# which sounds to play. Possible events: critical,
# warning, unknown, ok, up, down, unreachable,
# pending. Sounds are expected in the sounds subdirectory
# of htdocs (Default is /usr/share/check_mk/web/htdocs/sounds)
# sounds = [
#  ( "down", "down.wav" ),
#  ( "critical", "critical.wav" ),
#  ( "unknown", "unknown.wav" ),
#  ( "warning", "warning.wav" ),
#  ( None,      "ok", ), 
# ]
# Note: this example has not sound for unreachable hosts. 
# set sound_url to another url, if you place your sound
# files elsewhere:
# sound_url = "http://otherhost/path/to/sound/"
# or
# sound_url = "/nagios/alarms/"

# Tabs for choosing number of columns refresh
# view_option_refreshes = [ 30, 60, 90, 0 ]
# view_option_columns   = [ 1, 2, 3, 4, 5, 6, 8 ]

# Custom links for "Custom Links" Snapin. Feel free to add your
# own links here. The boolean values True and False determine
# wether the sections are open or closed by default.

# Links for everyone
custom_links['guest'] = [
  ( "Classical Nagios GUI", "../nagios/", "link_home.gif" ),
  ( "Addons", True, [
        ( "PNP4Nagios", "../pnp4nagios/",       "link_reporting.gif" ),
        ( "NagVis", False, [
            ( "Automap",    "../nagvis/index.php?map=__automap", "link_map.gif"),
            ( "Demo map",   "../nagvis/index.php?map=demo-map",  "link_map.gif"),
            ( "Demo Map 2", "../nagvis/index.php?map=demo2",     "link_map.gif"),
        ]),
  ]),
]

# The members of the role 'user' get the same links as the guests
# but some in addition
custom_links['user'] = custom_links['guest'] + [
  ( "Open Source Components", False, [
        ( "Multisite",     "http://mathias-kettner.de/checkmk_multisite.html" ),
        ( "MK Livestatus", "http://mathias-kettner.de/checkmk_livestatus.html" ),
        ( "Check_MK",      "http://mathias-kettner.de/check_mk.html" ),
        ( "Nagios",        "http://www.nagios.org/" ), 
        ( "PNP4Nagios",    "http://pnp4nagios.org/" ),
        ( "NagVis",        "http://nagvis.org/" ),
        ( "RRDTool",       "http://oss.oetiker.ch/rrdtool/" ),
   ])
]

# The admins yet get further links
custom_links['admin'] = custom_links['user'] + [
  ( "Support", False, [
      ( "Mathias Kettner",              "http://mathias-kettner.de/" ),
      ( "Check_MK Mailinglists",        "http://mathias-kettner.de/check_mk_lists.html" ),
      ( "Check_MK Portal (inofficial)", "http://check-mk-portal.org/"),
      ( "Nagios Portal (German)",       "http://nagios-portal.org"),
  ])
]

# Show error messages from unreachable sites in views. Set this
# to False in order to hide those messages.
show_livestatus_errors = True

# Hide certain views from the sidebar
# hidden_views = [ "hosttiles", "allhosts_mini" ]
# Vice versa: hide all views except these (be carefull, this

# will also exclude custom views)
# visible_views = [ "allhosts", "searchsvc" ]

# Load custom style sheet which can override styles defined in check_mk.css
# Put your style sheet into web/htdocs/
# custom_style_sheet = "my_styles.css"

# URL to show as welcome page (in the 'main' frame).
# You can use relative URL or absolute URLs like 'http://server/url'
# Default is 'main.py'
# start_url = 'view.py?view_name=hostgroups'

# Quicksearch: Limit the number of hits to shop in dropdown.
# Default is to show at most 80 items.
# quicksearch_dropdown_limit = 80

#   __        ___  _____ ___  
#   \ \      / / \|_   _/ _ \ 
#    \ \ /\ / / _ \ | || | | |
#     \ V  V / ___ \| || |_| |
#      \_/\_/_/   \_\_| \___/ 
#                             
# Check_MK's Web Administration Tool

# Declare files in conf.d/ to be editable with WATO. Please make
# sure, that those files exist and are writable by Apache, e.g.:
# touch /etc/check_mk/conf.d/network.mk
# chgrp www /etc/check_mk/conf.d/network.mk
# chmod 664 /etc/check_mk/conf.d/network.mk
# 
# config_files = [
#   ("network.mk",    "Network, Infrastructure", [ "admin", "user" ] ),
#   ("datacenter.mk", "Servers in Datacenter",   [ "admin" ]),
# ]

# Host tags to be used in WATO
# host_tags = [
#  ( "Operating System", [
#       ( "lnx", "Linux", [ 'tcp' ]),
#       ( "win", "Windows", [ 'tcp', 'snmp' ]),
#       ( "net", "Network device", [ 'snmp' ]),
#       ( "ping", "Other PING-only device", ),
#    ]),
#  ( "Productivity", [
#       ( "prod", "Production System" ),
#       ( "test", "Test System" ),
#    ]),
#  ( "Bulkwalk (SNMP v2c)", [
#       ( None,   "simple walk (SNMP v1)"),
#       ( "bulk", "Bulkwalk (SNMP v2c)" ),
#    ]),
# 
# ]

