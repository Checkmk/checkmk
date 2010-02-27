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

def set_default(d):
    global defaults
    defaults = d
    config_dir = defaults["var_dir"] + "/web" 

def load_config():
    # define default values for all settings
    filename = defaults["
    global debug
    debug = False
    global admin_users
    admin_users = []
    global guest_users
    guest_users = []
    global users
    users = []
    execfile(filename)
    global config_dir

def is_allowed_to_view(user):
   return multiadmin_users == None or user in multiadmin_users

def is_allowed_to_act(user):
   return multiadmin_action_users == None or user in multiadmin_action_users

# Returns true when restriction is disabled or restriction is enabled and the
# user is in the unrestricted list
def is_unrestricted_action_user(user):
    if multiadmin_restrict_actions or multiadmin_restrict:
        if user not in multiadmin_unrestricted_action_users:
            return False

    return True

# Returns true when restriction is disabled or restriction is enabled and the
# user is in the unrestricted list
def is_unrestricted_user(user):
    if multiadmin_restrict:
        if user not in multiadmin_unrestricted_users:
            return False

    return True

def sitenames():
    return sites.keys()

def sites():
    return dict( [(name, site(name)) for name in sitenames()])

def site(name):
    s = sites.get(name, {})
    if "alias" not in s:
	s["alias"] = name
    if "socket" not in s:
	s["socket"] = "unix:" + livestatus_unix_socket
    if "nagios_url" not in s:
	s["nagios_url"] = nagios_url
    if "nagios_cgi_url" not in s:
	s["nagios_cgi_url"] = nagios_cgi_url
    if "pnp_prefix" not in s:
	s["pnp_prefix"] = pnp_prefix
    return s 

def site_is_local(name):
    s = sites.get(name, {})
    sock = s.get("socket")
    return not sock or sock.startswith("unix:")

def is_multisite():
    return len(multiadmin_sites) > 1

