#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

# This is an example for a usage of Livestatus: it creates
# a NagVis map using actual live data from a running Nagios
# system. Most things are hardcoded here but this might by
# a useful example for coding your own stuff...

import livestatus

g_y = 50
y_title = 40
lineheight = 30
x_hostgroup = 30
x_therm = 200
x_usv = 560

def make_label(text, x, y, width):
    print """
define textbox {
    text=%s
    x=%d
    y=%d
    background_color=#C0C0C1
    border_color=#000055
    w=%d
}""" % (text, x, y, width)


def render_hostgroup(name, alias):
    global g_y
    g_y += lineheight

    # Name des Serverraums
    make_label(alias, x_hostgroup, g_y, x_therm - x_hostgroup - 20)
    def display_servicegroup(name, x):
	if live.query_value("GET servicegroups\nStats: name = %s\n" % name) == 1:
	    print """
define servicegroup {
	    servicegroup_name = %s
	    x=%d
	    y=%d
}""" % (name, x, g_y)

	    # Einzelauflistung der Thermometer
	    num = 0
	    shift = 16
	    for host, service in live.query("GET services\nFilter: groups >= %s\nColumns: host_name description" % name):
		num += 1
		print """
define service {
	    host_name=%s
	    service_description=%s
	    x=%d
	    y=%d
	    url=/pnp4nagios/graph?host=%s&srv=%s
}
    """ % (host, service, x + 30 + shift * num, g_y, host, service)

    # Gesamtzustand Thermometer
    display_servicegroup(name + "_therm", x_therm)

    # Auflistung der USV-Parameter
    display_servicegroup(name + "_usv", x_usv)
    



socket_path = "unix:/var/run/nagios/rw/live"
live = livestatus.SingleSiteConnection(socket_path)

print """
define global {
    allowed_for_config=nagiosadmin
	allowed_user=nagiosadmin
	map_image=demo_background.png
	iconset=std_medium
}
"""


# hostgroups = live.query("GET hostgroups\nColumns: name alias")
hostgroups = [
 ( "s02",   "S-02" ),
 ( "s06",   "S-06" ),
 ( "s48",   "S-48" ),
 ( "ad214", "AD-214" ),
 ( "ik026", "IK-026" ),
 ( "etage", "Etagenverteiler" ),
 ]
for name, alias in hostgroups:
   render_hostgroup(name, alias)

make_label("Temperaturen", x_therm, y_title, 250)
make_label("USV-Status",   x_usv,   y_title, 160)

