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

import check_mk

# TODO: Remove this. It is replace by side bar plugin?
# Or only show this, if sidebar snapin is not used?
def show_site_header(html):
    return False

    if check_mk.is_multisite():
	html.write("<table class=siteheader><tr>")
	for sitename in check_mk.sites():
	    site = check_mk.site(sitename)
	    state = html.site_status[sitename]["state"]
	    if state == "disabled":
		switch = "on"
	    else:
		switch = "off"
	    uri = html.makeuri([("_site_switch", sitename + ":" + switch)])
	    if check_mk.multiadmin_use_siteicons:
		html.write("<td>")
		add_site_icon(html, sitename)
		html.write("</td>")
	    html.write("<td class=%s>" % state)
	    html.write("<a href=\"%s\">%s</a></td>" % (uri, site["alias"]))
	html.write("</tr></table>\n")

def add_site_icon(html, sitename):
    if check_mk.multiadmin_use_siteicons:
	html.write("<img class=siteicon src=\"icons/site-%s-24.png\"> " % sitename)
        return True
    else:
	return False

def site_selector(html, htmlvar, enforce = True):
    if enforce:
        choices = []
    else:
	choices = [("","")]
    for sitename, state in html.site_status.items():
	if state["state"] == "online":
	    choices.append((sitename, check_mk.site(sitename)["alias"]))
    html.sorted_select(htmlvar, choices)
