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

import config, wato

#   +----------------------------------------------------------------------+
#   |                     __        ___  _____ ___                         |
#   |                     \ \      / / \|_   _/ _ \                        |
#   |                      \ \ /\ / / _ \ | || | | |                       |
#   |                       \ V  V / ___ \| || |_| |                       |
#   |                        \_/\_/_/   \_\_| \___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
def render_wato(mini):
    if not config.wato_enabled:
        html.write(_("WATO is disabled in <tt>multisite.mk</tt>."))
    elif not config.may("wato.use"):
        html.write(_("You are not allowed to use Check_MK's web configuration GUI."))
        return False

    if mini:
        html.icon_button("wato.py", _("Main Menu"), "home", target="main")
    else:
        iconlink(_("Main Menu"), "wato.py", "home")
    for mode, title, icon, permission, help in wato.modules:
        if "." not in permission:
            permission = "wato." + permission
        if config.may(permission) or config.may("wato.seeall"):
            url = "wato.py?mode=%s" % mode
            if mini:
                html.icon_button(url, title, icon, target="main")
            else:
                iconlink(title, url, icon)

    num_pending = wato.api.num_pending_changes()
    if num_pending:
        footnotelinks([(_("%d changes") % num_pending, "wato.py?mode=changelog")])


sidebar_snapins["admin"] = {
    "title" : _("WATO &middot; Configuration"),
    "description" : _("Direct access to WATO - the web administration GUI of Check_MK"),
    "render" : lambda: render_wato(False),
    "refresh" : 60, # refresh pending changes, if other user modifies something
    "allowed" : [ "admin", "user" ],
}

sidebar_snapins["admin_mini"] = {
    "title" : _("WATO &middot; Quickaccess"),
    "description" : _("Access to WATO modules with only icons (saves space)"),
    "render" : lambda: render_wato(True),
    "refresh" : 60, # refresh pending changes, if other user modifies something
    "allowed" : [ "admin", "user" ],
    "styles": """
#snapin_admin_mini {
    padding-top: 6px;
}
#snapin_admin_mini img {
    margin-right: 3.9px;
    margin-bottom: 4px;
    width: 18px;
    height: 18px;
    position: relative;
    left: 3px;
    padding: 0;
}

#snapin_admin_mini div.footnotelink {
    margin-top: -14px;
}
""",
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
            "Stats: state >= 0\n" \
            "Columns: filename"
    hosts = html.live.query(query)
    html.live.set_prepend_site(False)
    hosts.sort()

    def get_folder(path, num = 0):
        wato_folder = {}
        if wato.folder_config_exists(wato.root_dir + path):
            wato_folder = wato.load_folder(wato.root_dir + path, childs = False)

        return {
            'title':      wato_folder.get('title', path.split('/')[-1]),
            '.path':      path,
            '.num_hosts': num,
            '.folders':   {},
        }

    # After the query we have a list of lists where each
    # row is a folder with the number of hosts on this level.
    #
    # Now get number of hosts by folder
    # Count all childs for each folder
    user_folders = {}
    for site, wato_folder, num in hosts:
        # Remove leading /wato/
        wato_folder = wato_folder[6:]

        # Loop through all levels of this folder to add the
        # host count to all parent levels
        folder_parts = wato_folder.split('/')
        for num_parts in range(0, len(folder_parts)):
            this_folder = '/'.join(folder_parts[:num_parts])

            if this_folder not in user_folders:
                user_folders[this_folder] = get_folder(this_folder, num)
            else:
                user_folders[this_folder]['.num_hosts'] += num

    #
    # Now build the folder tree
    #
    for folder_path, folder in sorted(user_folders.items(), reverse = True):
        if not folder_path:
            continue
        folder_parts = folder_path.split('/')
        parent_folder = '/'.join(folder_parts[:-1])

        user_folders[parent_folder]['.folders'][folder_path] = folder
        del user_folders[folder_path]

    #
    # Render link target selection
    #
    selected_topic, selected_target = config.load_user_file("foldertree", (_('Hosts'), 'allhosts'))

    topic_views  = views_by_topic()
    topics = [ (t, t) for t, s in topic_views ]
    html.select("topic", topics, selected_topic, onchange = 'wato_tree_topic_changed(this)')
    html.write('<span class=left>%s</span>' % _('Topic:'))

    for topic, views in topic_views:
        targets = []
        for t, title, name in views:
            if config.visible_views and name not in config.visible_views:
                continue
            if config.hidden_views and name in config.hidden_views:
                continue
            if t == topic:
                if topic == _('Dashboards'):
                    name = 'dashboard|' + name
                targets.append((name, title))

        attrs = {}
        if topic != selected_topic:
            attrs['style'] = 'display:none'
            default = ''
        else:
            default = selected_target

        html.select("target_%s" % topic, targets, default, attrs = attrs, onchange = 'wato_tree_target_changed(this)')

    html.write('<span class=left>%s</span>' % _('View:'))

    # Now render the whole tree
    if user_folders:
        render_tree_folder(user_folders[''])

def render_tree_folder(f):
    subfolders = f.get(".folders", {})
    is_leaf = len(subfolders) == 0

    # Suppress indentation for non-emtpy root folder
    if f['.path'] == '' and is_leaf:
        html.write("<ul>") # empty root folder
    elif f and f['.path'] != '':
        html.write("<ul style='padding-left: 0px;'>")

    title = '<a href="#" onclick="wato_tree_click(\'%s\');">%s (%d)</a>' % (
            f[".path"], f["title"], f[".num_hosts"])

    if not is_leaf:
        html.begin_foldable_container('wato-hosts', "/" + f[".path"], False, title)
        for sf in wato.api.sort_by_title(subfolders.values()):
            render_tree_folder(sf)
        html.end_foldable_container()
    else:
        html.write("<li>" + title + "</li>")

    html.write("</ul>")

sidebar_snapins['wato_foldertree'] = {
    'title'       : _('Foldertree'),
    'description' : _('This snapin shows the folders defined in WATO. It can be used to open views filtered by the WATO folder.'),
    'render'      : render_wato_foldertree,
    'allowed'     : [ 'admin', 'user', 'guest' ],
    'styles'      : """
#snapin_wato_foldertree select {
    float: right;
    padding: 0;
    width:   190px;
    height: 19px;
    margin-bottom: 2px;
    background-color: #6da1b8;
    color: #fff;
    border-color: #123a4a;
    font-size: 8pt;
}
#snapin_wato_foldertree select option {
    background-color: #6da1b8;
}
#snapin_wato_foldertree span {
    margin-top: 1px;
    display: block;
    color:  #ffffff;
    height: 20px;
}
"""
}
