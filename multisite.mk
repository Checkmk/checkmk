# Confguration for Check_MK Multisite

# Users with unrestricted permissions
admin_users = [ "nagiosadmin" ]

# Users seeing all data but cannot do any action
# guest_users = [ "guest" ]

# A lists of all normal operational users allowed to use
# Multisite. If this variable is no set, then everybody with a correct
# HTTP login may use Multisite and gets the role "user"
# users       = [ "meier", "huber", "mueller" ]

# Users not explicitely being listed in admin_users or guest_users
# get the role "user" if they have a valid login. You can change this
# to "guest", "admin" or None by setting the following variable:
# default_user_role = "guest"

# Sites to connect to. If this variable is unset, a single
# connection to the local host is done.
# sites = {
#    # connect to local Nagios
#    "local" : {
#         "alias" : "Munich"
#    },
# 
#    # connect to remote site
#    "paris": {
#         "alias":          "Paris",
#         "socket":         "tcp:10.0.0.2:6557",
#         "nagios_url":     "/paris/nagios",
#         "nagios_cgi_url": "/paris/nagios/cgi-bin",
#         "pnp_url":        "/paris/pnp4nagios/",
#     },
# }

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


# Custom links for "Custom Links" Snapin. Feel free to add your
# own links here. The boolean values True and False determine
# wether the sections are open or closed by default.

# Links for everyone
custom_links['guest'] = [
  ( "Classical Nagios GUI", "/nagios/", "link_home.gif" ),
  ( "Addons", True, [
        ( "PNP4Nagios", "/pnp4nagios/",       "link_reporting.gif" ),
        ( "NagVis", False, [
            ( "Automap",    "/nagvis/index.php?map=__automap", "link_map.gif"),
            ( "Demo map",   "/nagvis/index.php?map=demo-map",  "link_map.gif"),
            ( "Demo Map 2", "/nagvis/index.php?map=demo2",     "link_map.gif"),
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
