#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

# The following debug code can be used to tackle a mod_python
# problem when using the local hierarchy for plugins that refer
# to the config module.
# import time, os
# fn = "/tmp/config.load.%d" % os.getpid()
# if os.path.exists(fn):
#     raise Exception("Mist: config zweimal geladen!!")
#
# file(fn, "a").write("[%d] Geladen: %s\n" % (os.getpid(), time.time()))

import os, pprint, glob
from lib import *
import defaults

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

user = None
user_id = None
user_role_ids = []

# Base directory of dynamic configuration
config_dir = defaults.var_dir + "/web"

# Detect if we are running on OMD
try:
    defaults.omd_site
except:
    defaults.omd_site = None
    defaults.omd_root = None

def include(filename):
    if not filename.startswith("/"):
        filename = defaults.default_config_dir + "/" + filename

    # Config file is obligatory. An empty example is installed
    # during setup.sh. Better signal an error then simply ignore
    # Absence.
    try:
        lm = os.stat(filename).st_mtime
        execfile(filename, globals(), globals())
        modification_timestamps.append(lm)
    except Exception, e:
        global user_id
        global roles
        user_id = "nobody"
        roles = {}
        raise MKConfigError("Cannot read configuration file %s: %s:" % (filename, e))

modification_timestamps = []

def load_config():
    # reset settings which can be changed at runtime to
    # default values. Otherwise they stick to their changed
    # value - within the Apache process that has answered
    # the query, if that variable is not explicitely defined
    # in multisite.mk
    global debug
    debug = False
    global profile
    profile = False
    global auth_type
    auth_type = 'basic'

    # Reset values that can be appended to. Otherwise
    # those lists will get longer for each web page called while
    # using the same Python interpreter (i.e. Apache process). 
    # Remember: the module config.py is only loaded once per process
    # and is being reused in later sessions.
    global aggregations
    aggregations = []

    global modification_timestamps
    modification_timestamps = []

    global wato_host_tags
    wato_host_tags = []

    global wato_aux_tags
    wato_aux_tags = []

    include("multisite.mk")

    # Load also recursively all files below multisite.d
    conf_dir = defaults.default_config_dir + "/multisite.d"
    filelist = []
    if os.path.isdir(conf_dir):
        for root, dirs, files in os.walk(conf_dir):
            for filename in files:
                if filename.endswith(".mk"):
                    filelist.append(root + "/" + filename)

    filelist.sort()
    for p in filelist:
        include(p)


# -------------------------------------------------------------------
#    ____                     _         _
#   |  _ \ ___ _ __ _ __ ___ (_)___ ___(_) ___  _ __  ___
#   | |_) / _ \ '__| '_ ` _ \| / __/ __| |/ _ \| '_ \/ __|
#   |  __/  __/ |  | | | | | | \__ \__ \ | (_) | | | \__ \
#   |_|   \___|_|  |_| |_| |_|_|___/___/_|\___/|_| |_|___/
#
# -------------------------------------------------------------------

builtin_role_ids = [ "user", "admin", "guest" ] # hard coded in various permissions
roles = {} # User supplied roles

# define default values for all settings
debug             = False
users             = []
admin_users       = []
guest_users       = []
default_user_role = "user"

# New style, used by WATO
multisite_users = {}

# Global table of available permissions. Plugins may add their own
# permissions
permissions_by_name  = {}
permissions_by_order = []
permission_sections  = {}

def declare_permission(name, title, description, defaults):
    perm = { "name" : name, "title" : title, "description" : description, "defaults" : defaults }

    # Detect if this permission has already been declared before
    # The dict value is replaced automatically but the list value
    # to be replaced -> INPLACE!
    if perm in permissions_by_order:
        permissions_by_order[permissions_by_order.index(perm)] = perm
    else:
        permissions_by_order.append(perm)

    permissions_by_name[name] = perm

def declare_permission_section(name, title):
    permission_sections[name] = title

declare_permission("use",
     _("Use Multisite at all"),
     _("Users without this permission are not let in at all"),
     [ "admin", "user", "guest" ])

declare_permission("edit_permissions",
     _("Configure permissions"),
     _("Configure, which user role has which permissions"),
     [ "admin" ])

declare_permission("see_all",
     _("See all Nagios objects"),
     _("See all objects regardless of contacts and contact groups. If combined with 'perform commands' then commands may be done on all objects."),
     [ "admin", "guest" ])

declare_permission("edit_views",
     _("Edit views"),
     _("Create own views and customize builtin views"),
     [ "admin", "user" ])

declare_permission("publish_views",
     _("Publish views"),
     _("Make views visible and usable for other users"),
     [ "admin", "user" ])

declare_permission("force_views",
     _("Modify builtin views"),
     _("Make own published views override builtin views for all users"),
     [ "admin" ])

declare_permission("view_option_columns",
     _("Change view display columns"),
     _("Interactively change the number of columns being displayed by a view (does not edit or customize the view)"),
     [ "admin", "user", "guest" ])

declare_permission("view_option_refresh",
     _("Change view display refresh"),
     _("Interactively change the automatic browser reload of a view being displayed (does not edit or customize the view)"),
     [ "admin", "user" ])

declare_permission("painter_options",
     _("Change column display options"),
     _("Some of the display columns offer options for customizing their output. "
     "For example time stamp columns can be displayed absolute, relative or "
     "in a mixed style. This permission allows the user to modify display options"),
     [ "admin", "user", "guest" ])

declare_permission("act",
     _("Perform commands"),
     _("Allows users to perform Nagios commands. If no further permissions are granted, actions can only be done on objects one is a contact for"),
     [ "admin", "user" ])


declare_permission("see_sidebar",
     _("Use Check_MK sidebar"),
     _("Without this permission the Check_MK sidebar will be invisible"),
     [ "admin", "user", "guest" ])

declare_permission("configure_sidebar",
     _("Configure sidebar"),
     _("This allows the user to add, move and remove sidebar snapins."),
     [ "admin", "user" ])


declare_permission('edit_profile',
    _('Edit the user profile'),
    _('Permits the user to change the user profile settings.'),
    [ 'admin', 'user' ]
)

declare_permission('change_password',
    _('Edit the user password'),
    _('Permits the user to change the password.'),
    [ 'admin', 'user' ]
)

declare_permission('logout',
    _('Logout'),
    _('Permits the user to logout.'),
    [ 'admin', 'user', 'guest' ]
)


# Compute permissions for HTTP user and set in
# global variables. Also store user.
def login(u):
    global user_id
    user_id = u

    # Determine the roles of the user. If the user is listed in
    # users, admin_users or guest_users in multisite.mk then we
    # give him the according roles. If the user has an explicit
    # profile in multisite_users (e.g. due to WATO), we rather
    # use that profile. Remaining (unknown) users get the default_user_role.
    # That can be set to None -> User has no permissions at all.
    global user_role_ids
    user_role_ids = roles_of_user(user_id)

    # Get base roles (admin/user/guest)
    global user_baserole_ids
    user_baserole_ids = base_roles_of(user_role_ids)

    # Get best base roles and use as "the" role of the user
    global user_baserole_id
    if "admin" in user_role_ids:
        user_baserole_id = "admin"
    elif "user" in user_role_ids:
        user_baserole_id = "user"
    else:
        user_baserole_id = "guest"

    # Prepare user object
    global user, user_alias
    if u in multisite_users:
        user = multisite_users[u]
        user_alias = user.get("alias", user_id)
    else:
        user = { "roles" : user_role_ids }
        user_alias = user_id

    # Prepare cache of already computed permissions
    global user_permissions
    user_permissions = {}

    # Make sure, admin can restore permissions in any case!
    if user_id in admin_users:
        user_permissions["use"] = True        # use Multisite
        user_permissions["wato.use"] = True   # enter WATO
        user_permissions["wato.edit"] = True  # make changes in WATO...
        user_permissions["wato.users"] = True # ... with access to user management

    # Prepare users' own configuration directory
    global user_confdir
    user_confdir = config_dir + "/" + user_id
    make_nagios_directory(user_confdir)

    # load current on/off-switching states of sites
    read_site_config()

def get_language(default = None):
    if default == None:
        default = default_language
    return user and user.get('language', default) or default

def roles_of_user(user):
    # Make sure, builtin roles are present, even if not modified
    # and saved with WATO.
    for br in builtin_role_ids:
        if br not in roles:
            roles[br] = {}

    if user in multisite_users:
        return multisite_users[user]["roles"]
    elif user in admin_users:
        return [ "admin" ]
    elif user in guest_users:
        return [ "guest" ]
    elif users != None and user in users:
        return [ "user" ]
    elif os.path.exists(config_dir + "/" + user + "/automation.secret"):
        return [ "guest" ] # unknown user with automation account
    elif default_user_role:
        return [ default_user_role ]
    else:
        return []

def alias_of_user(user):
    if user in multisite_users:
        return multisite_users[user].get("alias", user)
    else:
        return user


def base_roles_of(some_roles):
    base_roles = set([])
    for r in some_roles:
        if r in builtin_role_ids:
            base_roles.add(r)
        else:
            base_roles.add(roles[r]["basedon"])
    return list(base_roles)


def may_with_roles(some_role_ids, pname):
    # If at least one of the user's roles has this permission, it's fine
    for role_id in some_role_ids:
        role = roles[role_id]

        he_may = role.get("permissions", {}).get(pname)
        if he_may == None: # not explicitely listed -> take defaults
            if "basedon" in role:
                base_role_id = role["basedon"]
            else:
                base_role_id = role_id
            perm = permissions_by_name[pname]
            he_may = base_role_id in perm["defaults"]
        if he_may:
            return True
    return False


def may(pname):
    global user_permissions
    if pname in user_permissions:
        return user_permissions[pname]
    he_may = may_with_roles(user_role_ids, pname)
    user_permissions[pname] = he_may
    return he_may

def user_may(u, pname):
    return may_with_roles(roles_of_user(u), pname)

def need_permission(pname):
    if not may(pname):
        perm = permissions_by_name[pname]
        raise MKAuthException(_("We are sorry, but you lack the permission "
                              "for this operation. If you do not like this "
                              "then please ask you administrator to provide you with "
                              "the following permission: '<b>%s</b>'.") % perm["title"])

def get_role_permissions():
    role_permissions = {}
    # Loop all permissions
    # and for each permission loop all roles
    # and check wether it has the permission or not
    roleids = roles.keys()
    for perm in permissions_by_order:
        for role_id in roleids:
            if not role_id in role_permissions:
                role_permissions[role_id] = []

            if may_with_roles([role_id], perm['name']):
                role_permissions[role_id].append(perm['name'])
    return role_permissions


# -------------------------------------------------------------------
#    ____  _ _
#   / ___|(_) |_ ___  ___
#   \___ \| | __/ _ \/ __|
#    ___) | | ||  __/\__ \
#   |____/|_|\__\___||___/
#
# -------------------------------------------------------------------

sites = { "": {} }
use_siteicons = False

def sitenames():
    return sites.keys()

def allsites():
    return dict( [(name, site(name))
                  for name in sitenames()
                  if not site(name).get("disabled", False)] )

def site(name):
    s = sites.get(name, {})
    # Now make sure that all important keys are available.
    # Add missing entries by supplying default values.
    if "alias" not in s:
        s["alias"] = name
    if "socket" not in s:
        s["socket"] = "unix:" + defaults.livestatus_unix_socket
    if "url_prefix" not in s:
        s["url_prefix"] = "../" # relative URL from /check_mk/
    s["id"] = name
    return s

def site_is_local(name):
    s = sites.get(name, {})
    sock = s.get("socket")
    return not sock or sock.startswith("unix:")

def is_multisite():
    if len(sites) > 1:
        return True
    elif len(sites) == 0:
        return False
    # Also use Multisite mode if the one and only site is not local
    sitename = sites.keys()[0]
    return not site_is_local(sitename)

def read_site_config():
    global user_siteconf
    user_siteconf = load_user_file("siteconfig", {})

def save_site_config():
    save_user_file("siteconfig", user_siteconf)

#    ____  _     _      _
#   / ___|(_) __| | ___| |__   __ _ _ __
#   \___ \| |/ _` |/ _ \ '_ \ / _` | '__|
#    ___) | | (_| |  __/ |_) | (_| | |
#   |____/|_|\__,_|\___|_.__/ \__,_|_|
#

sidebar = \
[('tactical_overview', 'open'),
 ('search',            'open'),
 ('views',             'open'),
 ('bookmarks',         'open'),
 ('admin',             'open'),
 ('master_control',    'closed')]

#    _     _           _ _
#   | |   (_)_ __ ___ (_) |_ ___
#   | |   | | '_ ` _ \| | __/ __|
#   | |___| | | | | | | | |_\__ \
#   |_____|_|_| |_| |_|_|\__|___/
#

soft_query_limit = 1000
hard_query_limit = 5000

declare_permission("ignore_soft_limit",
     "Ignore soft query limit",
     "Allows to ignore the soft query limit imposed upon the number of datasets returned by a query",
     [ "admin", "user" ])

declare_permission("ignore_hard_limit",
     "Ignore hard query limit",
     "Allows to ignore the hard query limit imposed upon the number of datasets returned by a query",
     [ "admin" ])

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

# Helper functions
def load_user_file(name, deflt):
    path = user_confdir + "/" + name + ".mk"
    try:
        return eval(file(path).read())
    except:
        return deflt

def save_user_file(name, content):
    path = user_confdir + "/" + name + ".mk"
    try:
        write_settings_file(path, content)
    except Exception, e:
        raise MKConfigError("Cannot save %s options for user <b>%s</b> into <b>%s</b>: %s" % \
                (name, user, path, e))


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

# Set this to a list in order to globally control which views are
# being displayed in the sidebar snapin "Views"
visible_views = None
# Set this list in order to actively hide certain views
hidden_views = None

# Custom user stylesheet to load (resides in htdocs/)
custom_style_sheet = None

# URL for start page in main frame (welcome page)
start_url = "dashboard.py"

# Timeout for rescheduling of host- and servicechecks
reschedule_timeout = 10.0

# Number of columsn in "Filter" form
filter_columns = 2

# Default language for l10n
default_language = None

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

#    __        ___  _____ ___
#    \ \      / / \|_   _/ _ \
#     \ \ /\ / / _ \ | || | | |
#      \ V  V / ___ \| || |_| |
#       \_/\_/_/   \_\_| \___/
#

wato_enabled = True
wato_host_tags = []
wato_aux_tags = []
wato_hide_filenames = True
wato_max_snapshots = 50
wato_num_hostspecs = 12
wato_num_itemspecs = 15
wato_activation_method = 'restart'
wato_write_nagvis_auth = False


#     ____ ___
#    | __ )_ _|
#    |  _ \| |
#    | |_) | |
#    |____/___|
#

ALL_HOSTS = '(.*)'
HOST_STATE = ('__HOST_STATE__',)
HIDDEN = ('__HIDDEN__',)
class FOREACH_HOST: pass
class FOREACH_SERVICE: pass
class REMAINING: pass
aggregation_rules = {}
aggregations = []
aggregation_functions = {}

