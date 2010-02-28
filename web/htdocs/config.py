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

import os, pprint
from lib import *

def set_defaults(d):
    global defaults
    defaults = d
    global config_dir
    config_dir = defaults["var_dir"] + "/web"

def load_config():
    filename = defaults["default_config_dir"] + "/multisite.mk"

    # Config file is obligatory. An empty example is installed
    # during setup.sh. Better signal an error then simply ignore
    # Absence.
    try:
        execfile(filename, globals(), globals())
    except Exception, e:
        global user
	global role
        global user_permissions
        user = "nobody"
        role = None
        user_permissions = []
        raise MKConfigError("Cannot read configuration file %s: %s:" % (filename, e))

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
debug       = False
users       = None  # None means: all
admin_users = []
guest_users = []

# Global table of available permissions. Plugins may add their own
# permissions
permissions_by_name = {}
permissions_by_order = []

def declare_permission(name, title, description, defaults):
    perm = { "name" : name, "title" : title, "description" : description, "defaults" : defaults }
    permissions_by_name[name] = perm
    permissions_by_order.append(perm)

declare_permission("use",
     "Use Multisite at all",
     "Users without this permission are not let in at all",
     [ "admin", "user", "guest" ])

declare_permission("edit_permissions",
     "Configure permissions",
     "Configure, which user role has which permissions",
     [ "admin" ])

declare_permission("act",
     "Perform commands",
     "Allows users to perform Nagios commands. If now futher permissions are granted, actions can only be done one objects one is a contact for",
     [ "admin", "user" ])

declare_permission("see_all",
     "See all Nagios objects",
     "See all objects regardless of contacts and contact groups",
     [ "admin", "guest" ])

declare_permission("act_all",
     "Commands on all objects",
     "Do all commands on all objects, regardless of contacts",
     [ "admin" ])

declare_permission("edit_views",
     "Edit views",
     "Create own views and customize builtin views",
     [ "admin", "user" ])

declare_permission("publish_views",
     "Plublish views",
     "Make views visible and usable for other users",
     [ "admin", "user" ])

declare_permission("force_views",
     "Override builtin views",
     "Make own published views override builtin views for all users",
     [ "admin" ])

declare_permission("see_sidebar",
     "Use Check_MK sidebar",
     "Without this permission the Check_MK sidebar will be invisible",
     [ "admin", "user", "guest" ])



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
    try:
        os.mkdir(user_confdir)
    except:
        pass

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
    path = user_confdir + "/siteconfig.mk"
    try:
        file(path, "w").write(pprint.pformat(user_siteconf) + "\n")
    except Exception, e:
        raise MKConfigError("Cannot save site configuration for user <b>%s</b> into <b>%s</b>: %s" % \
                (user, path, e))

def role_of_user(u):
    if u in admin_users:
        return "admin"
    elif u in guest_users:
        return "guest"
    elif users != None and u not in users:
        return None
    else:
        return "user"

def may(permname):
    return permname in user_permissions

def user_may(u, permname):
    role = role_of_user(u)
    roles = permissions.get(permname, permissions_by_name[permname]["defaults"])
    return role in roles 

def load_permissions():
    global permissions
    path = config_dir + "/permissions.mk"
    if os.path.exists(path):
	permissions = eval(file(path).read())
    else:
	permissions = {}

def save_permissions(permissions):
    file(config_dir + "/permissions.mk", "w").write(pprint.pformat(permissions) + "\n")

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
    if "alias" not in s:
        s["alias"] = name
    if "socket" not in s:
        s["socket"] = "unix:" + defaults["livestatus_unix_socket"]
    if "nagios_url" not in s:
        s["nagios_url"] = defaults["nagios_url"]
    if "nagios_cgi_url" not in s:
        s["nagios_cgi_url"] = defaults["nagios_cgi_url"]
    if "pnp_prefix" not in s:
        s["pnp_prefix"] = defaults["pnp_prefix"]
    return s

def site_is_local(name):
    s = sites.get(name, {})
    sock = s.get("socket")
    return not sock or sock.startswith("unix:")

def is_multisite():
    return len(sites) > 1

def read_site_config():
    path = user_confdir + "/siteconf.mk"
    global user_siteconf
    if os.path.exists(path):
        user_siteconf = eval(file(path).read())
    else:
        user_siteconf = {}



sidebar  = [('admin', 'open'), ('tactical_overview', 'open'), ('sitestatus', 'open'), \
        ('search', 'open'), ('views', 'open'), ('hostgroups', 'closed'), \
        ('servicegroups', 'closed'), ('hosts', 'closed'), ('time', 'open'), \
        ('nagios_legacy', 'closed'), ('performance', 'closed'), ('master_control', 'closed'), ('about', 'closed')]
