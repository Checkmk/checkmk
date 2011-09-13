#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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
role = None

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
        global user
        global role
        global user_permissions
        user = "nobody"
        role = None
        user_permissions = []
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

    # Reset values that can be appended to
    global aggregations
    aggregations = []

    global modification_timestamps
    modification_timestamps = []

    include("multisite.mk")
    # Load also all files below multisite.d
    conf_dir = defaults.default_config_dir + "/multisite.d"
    if os.path.isdir(conf_dir):
        filelist = glob.glob(conf_dir + "/*.mk")
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

roles = [ "user", "admin", "guest" ]

# define default values for all settings
debug             = False
users             = []
admin_users       = []
guest_users       = []
default_user_role = "user"

# Global table of available permissions. Plugins may add their own
# permissions
permissions_by_name  = {}
permissions_by_order = []
permission_sections  = {}

def declare_permission(name, title, description, defaults):
    perm = { "name" : name, "title" : title, "description" : description, "defaults" : defaults }
    permissions_by_name[name] = perm
    permissions_by_order.append(perm)

def declare_permission_section(name, title):
    permission_sections[name] = title

declare_permission("use",
     "Use Multisite at all",
     "Users without this permission are not let in at all",
     [ "admin", "user", "guest" ])

declare_permission("edit_permissions",
     "Configure permissions",
     "Configure, which user role has which permissions",
     [ "admin" ])

declare_permission("see_all",
     "See all Nagios objects",
     "See all objects regardless of contacts and contact groups. If combined<br>with 'perform commands' then commands may be done on all objects.",
     [ "admin", "guest" ])

declare_permission("edit_views",
     "Edit views",
     "Create own views and customize builtin views",
     [ "admin", "user" ])

declare_permission("publish_views",
     "Publish views",
     "Make views visible and usable for other users",
     [ "admin", "user" ])

declare_permission("force_views",
     "Modify builtin views",
     "Make own published views override builtin views for all users",
     [ "admin" ])

declare_permission("view_option_columns",
     "Change view display columns",
     "Interactively change the number of columns being displayed by a view<br>(does not edit or customize the view)",
     [ "admin", "user", "guest" ])

declare_permission("view_option_refresh",
     "Change view display refresh",
     "Interactively change the automatic browser reload of a view being displayed<br>(does not edit or customize the view)",
     [ "admin", "user" ])

declare_permission("painter_options",
     "Change column display options",
     "Some of the display columns offer options for customizing their output.<br>"
     "For example time stamp columns can be displayed absolute, relative or<br>"
     "in a mixed style. This permission allows the user to modify display options",
     [ "admin", "user", "guest" ])

declare_permission("act",
     "Perform commands",
     "Allows users to perform Nagios commands. If now futher permissions are granted,<br>actions can only be done one objects one is a contact for",
     [ "admin", "user" ])


declare_permission("see_sidebar",
     "Use Check_MK sidebar",
     "Without this permission the Check_MK sidebar will be invisible",
     [ "admin", "user", "guest" ])

declare_permission("configure_sidebar",
     "Configure sidebar",
     "This allows the user to add, move and remove sidebar snapins.",
     [ "admin", "user" ])



# Compute permissions for HTTP user and set in
# global variables. Also store user.
def login(u):
    global user
    user = u
    global role
    role = None

    # Prepare users' own configuration directory
    global user_confdir
    user_confdir = config_dir + "/" + user
    make_nagios_directory(user_confdir)

    # determine role of user. Each user may be listed only once
    # in admin_users, guest_users and users.
    all = admin_users + guest_users
    if users != None:
        all += users
    if all.count(user) > 1:
        raise MKConfigError("Your username (<b>%s</b>) is listed more than once "
                "in multisite.mk. This is not allowed. "
                "Please check your config." % user)

    role = role_of_user(user)

    # Now set permissions according to role
    load_permissions()
    global user_permissions
    user_permissions = set([])
    for p in permissions_by_order:
        roles = permissions.get(p["name"], p["defaults"])
        if role in roles:
            user_permissions.add(p["name"])

    # Make sure, admin can restore permissions in any case!
    if role == "admin":
        user_permissions.add("use")
        user_permissions.add("edit_permissions")

    read_site_config()

def save_site_config():
    save_user_file("siteconfig", user_siteconf)

def role_of_user(u):
    if u in admin_users:
        return "admin"
    elif u in guest_users:
        return "guest"
    elif u in users:
        return "user"
    else:
        return default_user_role

def may(permname):
    # handle case where declare_permission is done after login
    # and permname also not contained in save configuration
    if permname not in user_permissions:
        perm = permissions_by_name.get(permname)
        if not perm: # Object does not exists, e.g. sidesnap.multisite if not is_multisite()
            return False
        if role in perm["defaults"]:
            user_permissions.add(permname)

    return permname in user_permissions

def user_may(u, permname):
    role = role_of_user(u)
    roles = permissions.get(permname)
    if roles == None:
        perm = permissions_by_name.get(permname)
        if not perm:
            return False # permission target does not exist
        roles = perm["defaults"]
    return role in roles

def load_permissions():
    global permissions
    path = config_dir + "/permissions.mk"
    if os.path.exists(path):
        permissions = eval(file(path).read())
    else:
        permissions = {}

def save_permissions(permissions):
    write_settings_file(config_dir + "/permissions.mk", permissions)

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
    return dict( [(name, site(name)) for name in sitenames()])

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
    return s

def site_is_local(name):
    s = sites.get(name, {})
    sock = s.get("socket")
    return not sock or sock.startswith("unix:")

def is_multisite():
    if len(sites) > 1:
        return True
    # Also use Multisite mode if the one and only site is not local
    sitename = sites.keys()[0]
    return not site_is_local(sitename)

def read_site_config():
    global user_siteconf
    user_siteconf = load_user_file("siteconfig", {})

#    ____  _     _      _
#   / ___|(_) __| | ___| |__   __ _ _ __
#   \___ \| |/ _` |/ _ \ '_ \ / _` | '__|
#    ___) | | (_| |  __/ |_) | (_| | |
#   |____/|_|\__,_|\___|_.__/ \__,_|_|
#

sidebar = \
[('tactical_overview', 'open'),
 ('search',            'open'),
 ('wato',              'open'),
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
sounds = []

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


#    __        ___  _____ ___  
#    \ \      / / \|_   _/ _ \ 
#     \ \ /\ / / _ \ | || | | |
#      \ V  V / ___ \| || |_| |
#       \_/\_/_/   \_\_| \___/ 
#                              

wato_enabled = True
wato_host_tags = []
wato_hide_filenames = True
wato_max_snapshots = 50


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

