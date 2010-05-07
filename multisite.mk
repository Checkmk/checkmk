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
