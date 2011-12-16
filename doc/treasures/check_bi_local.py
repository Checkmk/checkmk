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

#!/usr/bin/python

# Example for creating real Nagios checks from BI
# aggregations. You need to create a view with
# the name aggr_service with the two columns
# Aggr State and Aggr Name.

import os

url = 'http://omdadmin:omd@localhost/bi/check_mk/view.py?view_name=aggr_webservice&output_format=python'

data = eval(os.popen("curl --silent '%s'" % url).read())

states = {
  "OK"      : 0,
  "WARN"    : 1,
  "CRIT"    : 2,
  "UNKNOWN" : 3,
}

for state, name in data[1:]:
    state_nr = states.get(state, -1)
    descr = "BI_Aggr_" + name.replace(" ", "_")
    if state_nr != -1:
        print "%d %s - %s" % (state_nr, descr, state)

