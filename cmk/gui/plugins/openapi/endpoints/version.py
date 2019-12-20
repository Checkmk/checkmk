#!/usr/bin/python
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import sys

import cmk
from cmk.gui.globals import request


def search(user=None, token_info=None):
    return {
        "site": cmk.omd_site(),
        "group": request.environ.get('mod_wsgi.application_group', 'unknown'),
        "versions": {
            "apache": request.environ.get('apache.version', 'unknown'),
            "checkmk": cmk.omd_version(),
            "python": sys.version,
            'mod_wsgi': request.environ.get('mod_wsgi.version', 'unknown'),
            'wsgi': request.environ['wsgi.version'],
        },
        "edition": cmk.edition_short(),
        "demo": cmk.is_demo(),
    }
