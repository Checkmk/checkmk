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

import pwd, defaults, pprint, os

nagios_state_names = { 0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN", 4: "DEPENDENT" }
nagios_short_state_names = { 0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKN", 4: "DEP" }
nagios_short_host_state_names = { 0: "UP", 1: "DOWN", 2: "UNREACH" }

class MKGeneralException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return str(self.reason)

class MKAuthException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return str(self.reason)

class MKConfigError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class MKUserError(Exception):
    def __init__(self, varname, msg):
        self.varname = varname
        self.message = msg
        Exception.__init__(self, msg)

class MKInternalError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

# Create directory owned by common group of Nagios and webserver,
# and make it writable for the group
def make_nagios_directory(path):
    if not os.path.exists(path):
        os.mkdir(path)
        gid = pwd.getpwnam(defaults.www_group).pw_gid
        os.chown(path, -1, gid)
        os.chmod(path, 0770)

def write_settings_file(path, content):
    file(path, "w", 0).write(pprint.pformat(content) + "\n")
    gid = pwd.getpwnam(defaults.www_group).pw_gid
    os.chown(path, -1, gid)
    os.chmod(path, 0660)
