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


# Still missing:
# * Permissions for actions


def page_view_permissions():
    html.header("My permissions")
    html.write("<p>You have the following permissions:</p>")
    html.write("<h2>General permissions</h2>\n<ul>")
    current_section = None
    for perm in config.permissions_by_order:
        pname = perm["name"]
        if config.may(pname):
            if "." in pname:
                section = pname.split(".")[0]
                section_title = config.permission_sections[section]
                if section != current_section:
                    current_section = section
                    html.write("</ul>\n<h2>%s</h2><ul>\n" % section_title)

            html.write("<li>%s</li>\n" % perm["title"])
    html.write("</ul>\n")
    html.footer()

def page_edit_permissions():
    if not config.may("edit_permissions"):
        raise MKAuthException(_("You are not allowed to edit permissions."))

    html.header(_("Edit permissions"))

    permissions = {}
    if html.var("save"):
        for perm in config.permissions_by_order:
            mays = [ role for role in config.roles if html.var("p_%s_%s" % (role, perm["name"])) ]
            permissions[perm["name"]] = mays

        config.save_permissions(permissions)
        config.load_permissions()
        html.message(_("Permissions have been saved."))

    def section_header(section_title, is_open=False):
        html.begin_foldable_container('permissions', section_title, is_open, section_title, indent=False) 
        html.write('<table class="form permissions">\n')
        html.write("<th>Permission</th>\n")
        for role in config.roles:
            html.write("<th>%s</th>" % role)
        html.write("</tr>\n")

    def section_footer():
        html.write("</table>")
        html.end_foldable_container()


    html.begin_form("permissions", method="POST")
    section_header(_("General permissions"), True)

    current_section = None
    for perm in config.permissions_by_order:
        pname = perm["name"]
        if "." in pname:
            section = pname.split(".")[0]
            section_title = config.permission_sections[section]
            if section != current_section:
                section_footer()
                section_header(section_title)
                current_section = section

        title = "<b>%s</b><br><i>%s</i>" % (perm["title"], perm["description"])
        classes="legend border"

        html.write("<tr><td class=\"%s\">%s</td>" % (classes, title))
        for role in config.roles:
            current = role in config.permissions.get(pname, perm["defaults"])
            html.write("<td class=\"content %s\">" % role)
            html.checkbox("p_%s_%s" % (role, pname), current)
            html.write("</td>")
        html.write("</tr>\n")

    section_footer()


    html.write("<br>")
    html.button("save", _("Save"))
    html.end_form()
    html.footer()
