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

import config, htmllib, pprint, sidebar
from lib import *

def declare_external_permissions():
    sidebar.declare_permissions()
# views.declare_permissions()
# actions.declare_permissions()

def page_view_permissions(h):
    global html
    html = h
    declare_external_permissions()
    html.header("My permissions")
    html.write("<p>You have the following permissions:</p>")
    html.write("<table class=permissions>\n")
    for perm in config.permissions_by_order:
	if config.may(perm["name"]):
	    html.write("<tr><td>%s</td></tr>\n" % perm["title"])
    html.write("</table>\n")
    html.footer()

def page_edit_permissions(h):
    global html
    html = h
    if not config.may("edit_permissions"):
	raise MKAuthException("You are not allowed to edit permissions.")
    declare_external_permissions()

    html.header("Edit permissions")

    permissions = {}
    if html.var("save"):
	for perm in config.permissions_by_order:
	    mays = [ role for role in config.roles if html.var("p_%s_%s" % (role, perm["name"])) ]
	    permissions[perm["name"]] = mays
	
	config.save_permissions(permissions)	
	config.load_permissions()
	html.message("Permissions have beend saved.")


    html.begin_form("permissions")
    html.write("<table class=permissions>\n")
    html.write("<th>Permission</th>\n")
    for role in config.roles:
	html.write("<th>%s</th>" % role)
    html.write("</tr>\n")

    for perm in config.permissions_by_order:
	html.write("<tr><td class=legend><b>%s</b><br><i>%s</i></td>" % (perm["title"], perm["description"]))
	for role in config.roles:
	    current = role in config.permissions[perm["name"]]
	    html.write("<td class=\"content %s\">" % role)
	    html.checkbox("p_%s_%s" % (role, perm["name"]), current)
	    html.write("</td>")
	html.write("</tr>\n")

    html.write("<tr><td class=legend colspan=%d>" % (1 + len(config.roles)))
    html.button("save", "Save")
    html.write("</td></tr>\n")
    html.write("</table>\n")
    html.end_form()
    html.footer()
