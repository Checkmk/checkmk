# Confguration for Check_MK Multisite

# Users with unrestricted permissions
admin_users = [ "nagiosadmin" ]

# Users seeing all data but cannot do any action
# guest_users = [ "guest" ]

# A lists of all normal operational users allowed to use
# Multisite. If this variable is no set, then everybody with a correct
# HTTP login may use Multisite, but sees only data he/she is
# a contact for in Nagios
# users       = [ "meier", "huber", "mueller" ]

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
#         "pnp_prefix":     "/paris/pnp4nagios/graph",
#     },
# }

# Restrict number of datasets queries via Livestatus.
# This prevents you from consuming too much ressources
# in case of insensible queries.
# soft_query_limit = 1000
# hard_query_limit = 5000
