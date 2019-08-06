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

import cmk.gui.config as config
import cmk.gui.wato as wato
import cmk.gui.views as views
import cmk.gui.dashboard as dashboard
import cmk.gui.watolib as watolib
import cmk.gui.sites as sites
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    iconlink,
    footnotelinks,
    visuals_by_topic,
)


def render_wato(mini):
    if not config.wato_enabled:
        html.write_text(_("WATO is disabled."))
        return False
    elif not config.user.may("wato.use"):
        html.write_text(_("You are not allowed to use Check_MK's web configuration GUI."))
        return False

    if mini:
        html.icon_button("wato.py", _("Main Menu"), "home", target="main")
    else:
        iconlink(_("Main Menu"), "wato.py", "home")

    for module in wato.get_modules():
        if not module.may_see():
            continue

        url = module.get_url()
        if mini:
            html.icon_button(url, module.title, module.icon, target="main")
        else:
            iconlink(module.title, url, module.icon)

    pending_info = watolib.get_pending_changes_info()
    if pending_info:
        footnotelinks([(pending_info, "wato.py?mode=changelog")])
        html.div('', class_="clear")


@snapin_registry.register
class SidebarSnapinWATO(SidebarSnapin):
    @staticmethod
    def type_name():
        return "admin"

    @classmethod
    def title(cls):
        return _("WATO &middot; Configuration")

    @classmethod
    def description(cls):
        return _("Direct access to WATO - the web administration GUI of Check_MK")

    @classmethod
    def allowed_roles(cls):
        return ["admin", "user"]

    # refresh pending changes, if other user modifies something
    @classmethod
    def refresh_regularly(cls):
        return True

    def show(self):
        render_wato(mini=False)


@snapin_registry.register
class SidebarSnapinWATOMini(SidebarSnapin):
    @staticmethod
    def type_name():
        return "admin_mini"

    @classmethod
    def title(cls):
        return _("WATO &middot; Quickaccess")

    @classmethod
    def description(cls):
        return _("Access to WATO modules with only icons (saves space)")

    @classmethod
    def allowed_roles(cls):
        return ["admin", "user"]

    # refresh pending changes, if other user modifies something
    @classmethod
    def refresh_regularly(cls):
        return True

    def show(self):
        render_wato(mini=True)


def compute_foldertree():
    sites.live().set_prepend_site(True)
    query = "GET hosts\n" \
            "Stats: state >= 0\n" \
            "Columns: filename"
    hosts = sites.live().query(query)
    sites.live().set_prepend_site(False)
    hosts.sort()

    def get_folder(path, num=0):
        folder = watolib.Folder.folder(path)
        return {
            'title': folder.title() or path.split('/')[-1],
            '.path': path,
            '.num_hosts': num,
            '.folders': {},
        }

    # After the query we have a list of lists where each
    # row is a folder with the number of hosts on this level.
    #
    # Now get number of hosts by folder
    # Count all childs for each folder
    user_folders = {}
    for _site, filename, num in hosts:
        # Remove leading /wato/
        wato_folder_path = filename[6:]

        # Loop through all levels of this folder to add the
        # host count to all parent levels
        path_parts = wato_folder_path.split('/')
        for num_parts in range(0, len(path_parts)):
            this_folder_path = '/'.join(path_parts[:num_parts])

            if watolib.Folder.folder_exists(this_folder_path):
                if this_folder_path not in user_folders:
                    user_folders[this_folder_path] = get_folder(this_folder_path, num)
                else:
                    user_folders[this_folder_path]['.num_hosts'] += num

    #
    # Now build the folder tree
    #
    for folder_path, folder in sorted(user_folders.items(), reverse=True):
        if not folder_path:
            continue
        folder_parts = folder_path.split('/')
        parent_folder = '/'.join(folder_parts[:-1])

        user_folders[parent_folder]['.folders'][folder_path] = folder
        del user_folders[folder_path]

    #
    # Now reduce the tree by e.g. removing top-level parts which the user is not
    # permitted to see directly. Example:
    # Locations
    #  -> Hamburg: Permitted to see all hosts
    #  -> Munich:  Permitted to see no host
    # In this case, where only a single child with hosts is available, remove the
    # top level
    def reduce_tree(folders):
        for folder_path, folder in folders.items():
            if len(folder['.folders']) == 1 and folder['.num_hosts'] == 0:
                child_path, child_folder = folder['.folders'].items()[0]
                folders[child_path] = child_folder
                del folders[folder_path]

                reduce_tree(folders)

    reduce_tree(user_folders)
    return user_folders


# Note: the dictionary that represents the folder here is *not*
# the datastructure from WATO but a result of compute_foldertree(). The reason:
# We fetch the information via livestatus - not from WATO.
def render_tree_folder(tree_id, folder, js_func):
    subfolders = folder.get(".folders", {}).values()
    subfolders.sort(key=lambda x: x["title"].lower())

    is_leaf = len(subfolders) == 0

    # Suppress indentation for non-emtpy root folder
    if folder['.path'] == '' and is_leaf:
        html.open_ul()  # empty root folder
    elif folder and folder['.path'] != '':
        html.open_ul(style="padding-left:0px;")

    title = html.render_a("%s (%d)" % (folder["title"], folder[".num_hosts"]),
                          href="#",
                          class_="link",
                          onclick="%s(this, \'%s\');" % (js_func, folder[".path"]))

    if not is_leaf:
        html.begin_foldable_container(tree_id, "/" + folder[".path"], False, HTML(title))
        for subfolder in subfolders:
            render_tree_folder(tree_id, subfolder, js_func)
        html.end_foldable_container()
    else:
        html.li(title)

    html.close_ul()


@snapin_registry.register
class SidebarSnapinWATOFoldertree(SidebarSnapin):
    @staticmethod
    def type_name():
        return "wato_foldertree"

    @classmethod
    def title(cls):
        return _('Tree of folders')

    @classmethod
    def description(cls):
        return _('This snapin shows the folders defined in WATO. It can be used to '
                 'open views filtered by the WATO folder. It works standalone, without '
                 'interaction with any other snapin.')

    def show(self):
        if not watolib.is_wato_slave_site():
            if not config.wato_enabled:
                html.write_text(_("WATO is disabled."))
                return False

        user_folders = compute_foldertree()

        #
        # Render link target selection
        #
        selected_topic, selected_target = config.user.load_file("foldertree",
                                                                (_('Hosts'), 'allhosts'))

        dashboard.load_dashboards()
        topic_views = visuals_by_topic(views.get_permitted_views().items() +
                                       dashboard.permitted_dashboards().items())
        topics = [(t, t) for t, _s in topic_views]

        html.open_table()
        html.open_tr()
        html.td(_('Topic:'), class_="label")
        html.open_td()
        html.dropdown("topic",
                      topics,
                      deflt=selected_topic,
                      onchange='cmk.sidebar.wato_tree_topic_changed(this)')
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.td(_("View:"), class_="label")
        html.open_td()

        for topic, view_list in topic_views:
            targets = []
            for t, title, name, is_view in view_list:
                if config.visible_views and name not in config.visible_views:
                    continue
                if config.hidden_views and name in config.hidden_views:
                    continue
                if t == topic:
                    if not is_view:
                        name = 'dashboard|' + name
                    targets.append((name, title))

            if topic != selected_topic:
                default, style = '', 'display:none'
            else:
                default, style = selected_target, None
            html.dropdown("target_%s" % topic,
                          targets,
                          deflt=default,
                          onchange='cmk.sidebar.wato_tree_target_changed(this)',
                          style=style)

        html.close_td()
        html.close_tr()
        html.close_table()

        # Now render the whole tree
        if user_folders:
            render_tree_folder("wato-hosts",
                               user_folders.values()[0], 'cmk.sidebar.wato_tree_click')


@snapin_registry.register
class SidebarSnapinWATOFolders(SidebarSnapin):
    @staticmethod
    def type_name():
        return "wato_folders"

    @classmethod
    def title(cls):
        return _('Folders')

    @classmethod
    def description(cls):
        return _('This snapin shows the folders defined in WATO. It can '
                 'be used to open views filtered by the WATO folder. This '
                 'snapin interacts with the "Views" snapin, when both are '
                 'enabled.')

    def show(self):
        user_folders = compute_foldertree()
        if user_folders:
            render_tree_folder("wato-folders",
                               user_folders.values()[0], 'cmk.sidebar.wato_folders_clicked')
