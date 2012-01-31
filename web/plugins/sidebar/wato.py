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

import config, wato

#   +----------------------------------------------------------------------+
#   |                     __        ___  _____ ___                         |
#   |                     \ \      / / \|_   _/ _ \                        |
#   |                      \ \ /\ / / _ \ | || | | |                       |
#   |                       \ V  V / ___ \| || |_| |                       |
#   |                        \_/\_/_/   \_\_| \___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
def render_wato():
    if not config.wato_enabled:
        html.write(_("WATO is disabled in <tt>multisite.mk</tt>."))
    elif not config.may("wato.use"):
        html.write(_("You are not allowed to use Check_MK's web configuration GUI."))
        return False

    iconlink(_("Main menu"), "wato.py", "home")
    for mode, title, icon, permission, help in wato.modules:
        if config.may("wato." + permission) or config.may("wato.seeall"):
            iconlink(title, "wato.py?mode=%s" % mode, icon)


sidebar_snapins["admin"] = {
    "title" : _("WATO &middot; Configuration"),
    "description" : _("Direct access to WATO - the web administration GUI of Check_MK"),
    "author" : "Mathias Kettner",
    "render" : render_wato,
    "allowed" : [ "admin", "user" ],
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
    if not config.wato_enabled:
        html.write(_("WATO is disabled in <tt>multisite.mk</tt>."))
    else:
        html.write(_('This snapin is deprecated. Please use the WATO foldertree snapin instead.'))

sidebar_snapins["wato"] = {
    "title" : _("Hosts"),
    "description" : _("A foldable tree showing all your WATO folders and files - "
                      "allowing you to navigate in the tree while using views or being in WATO"),
    "author" : "Mathias Kettner",
    "render" : render_wato_folders,
    "allowed" : [ "admin", "user", "guest" ],
}

#   .----------------------------------------------------------------------.
#   |            _____     _     _           _                             |
#   |           |  ___|__ | | __| | ___ _ __| |_ _ __ ___  ___             |
#   |           | |_ / _ \| |/ _` |/ _ \ '__| __| '__/ _ \/ _ \            |
#   |           |  _| (_) | | (_| |  __/ |  | |_| | |  __/  __/            |
#   |           |_|  \___/|_|\__,_|\___|_|   \__|_|  \___|\___|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_wato_foldertree():
    if not config.wato_enabled:
        html.write(_("WATO is disabled in <tt>multisite.mk</tt>."))
    else:
        render_wato_foldertree()

def render_wato_foldertree():
    html.live.set_prepend_site(True)
    query = "GET hosts\n" \
            "Columns: name host_filename"
    hosts = html.live.query(query)
    html.live.set_prepend_site(False)
    hosts.sort()

    # Get number of hosts by folder
    # Count all childs for each folder
    user_folders = {}
    for site, hostname, wato_folder in hosts:
        # Remove leading /wato/
        wato_folder = wato_folder[6:]

        # Loop through all levels of this folder to add the
        # host count to all parent levels
        folder_parts = wato_folder.split('/')
        for num_parts in range(0, len(folder_parts)):
            this_folder = '/'.join(folder_parts[:num_parts])

            if this_folder not in user_folders:
                user_folders[this_folder] = wato.api.get_folder(this_folder)
                user_folders[this_folder]['.num_hosts'] = 1
            else:
                user_folders[this_folder]['.num_hosts'] += 1

    # Update the WATO folder tree with the user specific permissions
    folder_tree = wato.api.get_folder_tree()
    def update_foldertree(f):
        this_path = f['.path']
        if this_path in user_folders:
            f['.num_hosts'] = user_folders[this_path]['.num_hosts']

        for subfolder_path, subfolder in f.get(".folders", {}).items():
            # Only handle paths which the user is able to see
            if subfolder['.path'] in user_folders:
                update_foldertree(subfolder)
            else:
                del f['.folders'][subfolder['.path']]
    update_foldertree(folder_tree)

    # Now render the whole tree
    render_tree_folder(folder_tree)

def render_tree_folder(f):
    subfolders = f.get(".folders", {})
    is_leaf = len(subfolders) == 0

    # Suppress indentation for non-emtpy root folder
    if ".parent" not in f and is_leaf:
        html.write("<ul>") # empty root folder
    elif ".parent" in f:
        html.write("<ul style='padding-left: 0px;'>")

    title = '<a href="#" onclick="wato_tree_click(%r);">%s (%d)</a>' % (
            f[".path"], f["title"], f[".num_hosts"])

    if not is_leaf:
        html.begin_foldable_container('wato-hosts', "/" + f[".path"], False, title)
        for sf in wato.api.sort_by_title(subfolders.values()):
            render_tree_folder(sf)
        html.end_foldable_container()
    else:
        html.write("<li>" + title + "</li>")
    if ".parent" in f or is_leaf:
        html.write("</ul>")

sidebar_snapins['wato_foldertree'] = {
    'title'       : _('WATO Foldertree'),
    'description' : _(''),
    'author'      : 'Lars Michelsen',
    'render'      : render_wato_foldertree,
    'allowed'     : [ 'admin', 'user', 'guest' ],
}
