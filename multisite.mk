# Confguration for Check_MK Multisite

# Users with unrestricted permissions. These users will always
# have the permissions to edit users, roles and permissions,
# even if configuration has been edited via WATO
admin_users = [ "nagiosadmin" ]

# NagVis
#
# The NagVis-Snapin needs to know the URL to nagvis.
# This is not always /nagvis/ - especially not for OMD
nagvis_base_url = '/nagvis'

# Views allow to play alarm sounds according to the
# "worst" state of the shown items. Enable sounds here:
# enable_sounds = True

# You can configure here which sounds to play. Possible events are "critical", 
# "warning", "unknown", "ok", "up", "down", "unreachable" and
# "pending". Sounds are expected in the sounds subdirectory
# of htdocs (Default is /usr/share/check_mk/web/htdocs/sounds). The
# following setting is the default:
# sounds = [
#  ( "down", "down.wav" ),
#  ( "critical", "critical.wav" ),
#  ( "unknown", "unknown.wav" ),
#  ( "warning", "warning.wav" ),
#  ( None,      "ok.wav" ), 
# ]

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
        ( "Multisite",     "http://mathias-kettner.de/checkmk_multisite.html", None, "_blank"),
        ( "MK Livestatus", "http://mathias-kettner.de/checkmk_livestatus.html", None, "_blank"),
        ( "Check_MK",      "http://mathias-kettner.de/check_mk.html", None, "_blank"),
        ( "Nagios",        "http://www.nagios.org/", None, "_blank"), 
        ( "PNP4Nagios",    "http://pnp4nagios.org/", None, "_blank"),
        ( "NagVis",        "http://nagvis.org/", None, "_blank"),
        ( "RRDTool",       "http://oss.oetiker.ch/rrdtool/", None, "_blank"),
   ])
]

# The admins yet get further links
custom_links['admin'] = custom_links['user'] + [
  ( "Support", False, [
      ( "Mathias Kettner",                "http://mathias-kettner.de/" ),
      ( "Check_MK Mailinglists",          "http://mathias-kettner.de/check_mk_lists.html" ),
      ( "Check_MK Exchange (inofficial)", "http://exchange.check-mk.org/", None, "_blank" ),
      ( "Nagios Portal (German)",         "http://nagios-portal.org", None, "_blank"),
  ])
]

# Hide certain views from the sidebar
# hidden_views = [ "hosttiles", "allhosts_mini" ]
# Vice versa: hide all views except these (be carefull, this

# will also exclude custom views)
# visible_views = [ "allhosts", "searchsvc" ]

# Load custom style sheet which can override styles defined in check_mk.css
# Put your style sheet into web/htdocs/
# custom_style_sheet = "my_styles.css"

#   __        ___  _____ ___  
#   \ \      / / \|_   _/ _ \ 
#    \ \ /\ / / _ \ | || | | |
#     \ V  V / ___ \| || |_| |
#      \_/\_/_/   \_\_| \___/ 
#                             
# Check_MK's Web Administration Tool

# If you do not like WATO, you can disable it:
# wato_enabled = False

# Host tags to be used in WATO
# wato_host_tags = [
#  ( "os_type", "Operating System", [
#       ( "lnx", "Linux", [ 'tcp' ],),
#       ( "win", "Windows", [ 'tcp', 'snmp' ]),
#       ( "net", "Network device", [ 'snmp' ]),
#       ( "ping", "Other PING-only device", ),
#    ]),
#  ( "prod", "Productivity", [
#       ( "prod", "Production System" ),
#       ( "test", "Test System" ),
#    ]),
#  ( "bulkwalk", "Bulkwalk (SNMP v2c)", [
#       ( None,   "simple walk (SNMP v1)"),
#       ( "bulk", "Bulkwalk (SNMP v2c)"),
#    ], [ 'snmp' ]), 
# 
# ]

