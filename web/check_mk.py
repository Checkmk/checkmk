#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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

# defaults_path and check_mk_path must be set by importer!
import transfer
defaults_path = transfer.defaults_path
execfile(transfer.check_mk_path + "/check_mk.py")

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
    return multiadmin_sites.keys()

def sites():
    return dict( [(name, site(name)) for name in sitenames()])

def site(name):
    s = multiadmin_sites.get(name, {})
    if "alias" not in s:
	s["alias"] = name
    if "socket" not in s:
	s["socket"] = "unix:" + livestatus_unix_socket
    if "nagios_url" not in s:
	s["nagios_url"] = nagios_url
    if "nagios_cgi_url" not in s:
	s["nagios_cgi_url"] = nagios_cgi_url
    return s 

def is_multisite():
    return len(multiadmin_sites) > 1

multisite_config_dir = var_dir + "/web"
