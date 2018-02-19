#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

import math, grp, pprint, os, errno, marshal, re, fcntl, time
import traceback
from cmk.regex import regex
import cmk.store as store
import cmk.paths

# Load all files below share/check_mk/web/plugins/WHAT into a
# specified context (global variables). Also honors the
# local-hierarchy for OMD
# TODO: Couldn't we precompile all our plugins during packaging to make loading faster?
# TODO: Replace the execfile thing by some more pythonic plugin structure. But this would
#       be a large rewrite :-/
def load_web_plugins(forwhat, globalvars):
    for plugins_path in [ cmk.paths.web_dir + "/plugins/" + forwhat,
                          cmk.paths.local_web_dir + "/plugins/" + forwhat ]:
        if not os.path.exists(plugins_path):
            continue

        for fn in sorted(os.listdir(plugins_path)):
            file_path = plugins_path + "/" + fn

            if fn.endswith(".py") and not os.path.exists(file_path + "c"):
                execfile(file_path, globalvars)

            elif fn.endswith(".pyc"):
                code_bytes = file(file_path).read()[8:]
                code = marshal.loads(code_bytes)
                exec code in globalvars
