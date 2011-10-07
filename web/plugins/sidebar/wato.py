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

import config, wato

def wato_snapins_allowed():
    if not config.wato_enabled:
        html.write(_("WATO is disabled. Please set <tt>wato_enabled = True</tt> in your <tt>multisite.mk</tt> if you want to use WATO."))
        return False

    elif not config.may("use_wato"):
        html.write(_("You are not allowed to use Check_MK's web configuration GUI."))
        return False
    else:
        return True



#   +----------------------------------------------------------------------+
#   |                     __        ___  _____ ___                         |
#   |                     \ \      / / \|_   _/ _ \                        |
#   |                      \ \ /\ / / _ \ | || | | |                       |
#   |                       \ V  V / ___ \| || |_| |                       |
#   |                        \_/\_/_/   \_\_| \___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
def render_wato():
    if not wato_snapins_allowed():
        return

    iconlink(_("Host management"),        "wato.py?mode=folder",         "folder")
    iconlink(_("Host search"),            "wato.py?mode=search",         "search")
    iconlink(_("Backup & Restore"),       "wato.py?mode=snapshot",       "backup")
    iconlink(_("Changelog & Activation"), "wato.py?mode=changelog",      "wato_changes")
    iconlink(_("Global settings"),        "wato.py?mode=globalvars",     "configuration")
    iconlink(_("Rulesets"),               "wato.py?mode=rulesets",       "rulesets")
    iconlink(_("Host Groups"),            "wato.py?mode=host_groups",    "hostgroups")
    iconlink(_("Service Groups"),         "wato.py?mode=service_groups", "servicegroups")
    iconlink(_("Users & Contacts"),       "wato.py?mode=users",          "contacts")
    iconlink(_("Roles"),                  "wato.py?mode=roles",          "roles")
    iconlink(_("Contact Groups"),         "wato.py?mode=contact_groups", "contactgroups")
    iconlink(_("Time Periods"),           "wato.py?mode=timeperiods",    "timeperiods")
    iconlink(_("Multisite Connections"),  "wato.py?mode=sites",          "sites")


sidebar_snapins["admin"] = {
    "title" : _("WATO: Check_MK Administration"),
    "description" : _("Direct access to WATO - the web administration GUI of Check_MK"),
    "author" : "Mathias Kettner",
    "render" : render_wato,
    "allowed" : [ "admin" ],
}


#   +----------------------------------------------------------------------+
#   |          _____     _     _              _____                        |
#   |         |  ___|__ | | __| | ___ _ __   |_   _| __ ___  ___           |
#   |         | |_ / _ \| |/ _` |/ _ \ '__|____| || '__/ _ \/ _ \          |
#   |         |  _| (_) | | (_| |  __/ | |_____| || | |  __/  __/          |
#   |         |_|  \___/|_|\__,_|\___|_|       |_||_|  \___|\___|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def render_wato_folders():
    if not wato_snapins_allowed():
        return
    else:
        #EE if config.is_multisite():
        #EE     sitenames = config.allsites().keys()
        #EE     sitenames.sort()
        #EE     for sitename in sitenames:
        #EE         site = config.sites[sitename]
        #EE         state = html.site_status[sitename]["state"]
        #EE         if state != "disabled":
        #EE             html.write("<h3>%s</h3>\n" % site["alias"])
        #EE             ajax_url = site["url_prefix"] + "check_mk/ajax_wato_folders.py"
        #EE             html.javascript("document.write(get_url_sync('%s'));" % ajax_url)
        #EE else:
            ajax_wato_folders()

def ajax_wato_folders():
    if config.may("use_wato"):
        render_linktree_folder(wato.api.get_folder_tree())

    
def render_linktree_folder(f):
    subfolders = f.get(".folders", {})
    is_leaf = len(subfolders) == 0 

    title = '<a href="#" onclick="wato_tree_click(%r);">%s (%d)</a>' % (
            f[".path"], f["title"], f[".total_hosts"]) 

    if not is_leaf:
        html.begin_foldable_container('wato', f[".path"], False, title)
        for sf in wato.api.sort_by_title(subfolders.values()):
            render_linktree_folder(sf)
        html.end_foldable_container()
    else:
        html.write("<li>" + title + "</li>")



sidebar_snapins["wato"] = {
    "title" : _("Hosts"),
    "description" : _("A foldable tree showing all your WATO folders and files - allowing you to navigate in the tree while using views or being in WATO"),
    "author" : "Mathias Kettner",
    "render" : render_wato_folders,
    "allowed" : [ "admin", "user" ],
}
