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

import defaults, config

def page_index():
    start_url = html.var("start_url", config.start_url)
    html.req.headers_out.add("Cache-Control", "max-age=7200, public");
    if "%s" in config.page_heading:
        heading = config.page_heading % (defaults.omd_site or "Multisite")
    else:
        heading = config.page_heading

    html.write("""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">
<html>
<head>
 <title>%s</title>
 <link rel="shortcut icon" href="images/favicon.ico" type="image/ico">
</head>
<frameset cols="280,*" frameborder="0" framespacing="0" border="0">
    <frame src="side.py" name="side" noresize scrolling="no">
    <frame src="%s" name="main" noresize>
</frameset>
</html>
""" % (heading, start_url))

def page_main():
    html.header("Check_MK Multisite")
    html.write("""
<p>Welcome to Check_MK Multisite - a new GUI for viewing status information
and controlling your monitoring system. Multisite is not just another GUI
for Nagios - it uses a completely new architecture and design scheme. It's
key benefits are:</p>
<ul>
<li>It is fast.</li>
<li>it is flexible.</li>
<li>It supports distributed monitoring.</li>
</ul>

<p>Multisite is completely based on
<a href="http://mathias-kettner.de/checkmk_livestatus.html">MK
Livestatus</a>, which is what makes it fast in the first place - especially
in huge installations with a large number of hosts and services. </p>

<p>User customizable <b>views</b> is what makes Multisite flexible. Customize
the builtin views or create completely own views in order to need your
demands.</p>

<p>Multisite supports distributed monitoring by allowing you to combine an
arbitrary number of Monitoring servers under a common visualisation layer,
without the need of a centralized data storage. No SQL database is needed.
No network traffic is generated due to the monitoring.</p>

<p>Please learn more about Multisite at its <a href="http://mathias-kettner.de/checkmk_multisite.html">Documentation home page</a>.</p>
""")
    html.footer()

# This function does nothing. The sites have already
# been reconfigured according to the variable _site_switch,
# because that variable is processed by connect_to_livestatus()
def ajax_switch_site():
    pass
