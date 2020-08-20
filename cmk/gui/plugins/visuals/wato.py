#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Tuple, Iterator

import cmk.gui.watolib as watolib
import cmk.gui.sites as sites
import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import Choices

from cmk.gui.plugins.visuals import (
    filter_registry,
    Filter,
)


@filter_registry.register_instance
class FilterWatoFolder(Filter):
    def __init__(self):
        super().__init__(ident="wato_folder",
                         title=_("WATO Folder"),
                         sort_index=10,
                         info="host",
                         htmlvars=["wato_folder"],
                         link_columns=[])
        self.last_wato_data_update = None

    def available(self):
        # This filter is also available on slave sites with disabled WATO
        # To determine if this site is a slave we check the existance of the distributed_wato.mk
        # file and the absence of any site configuration
        return config.wato_enabled or watolib.is_wato_slave_site()

    def load_wato_data(self):
        self.tree = watolib.Folder.root_folder()
        self.path_to_tree = {}  # will be filled by self.folder_selection
        self.selection = list(self.folder_selection(self.tree))
        self.last_wato_data_update = time.time()

    def check_wato_data_update(self):
        if not self.last_wato_data_update or time.time() - self.last_wato_data_update > 5:
            self.load_wato_data()

    def display(self):
        self.check_wato_data_update()
        # Note: WATO Folders that the user has not permissions to must not be visible.
        # Permissions in this case means, that the user has view permissions for at
        # least one host in that folder.
        result = sites.live().query(
            "GET hosts\nCache: reload\nColumns: filename\nStats: state >= 0\n")
        allowed_folders = {""}  # The root(Main directory)
        for path, _host_count in result:
            # convert '/wato/server/hosts.mk' to 'server'
            folder = path[6:-9]
            # allow the folder an all of its parents
            parts = folder.split("/")
            subfolder = ""
            for part in parts:
                if subfolder:
                    subfolder += "/"
                subfolder += part
                allowed_folders.add(subfolder)

        choices: Choices = [entry for entry in self.selection if entry[0] in allowed_folders]
        html.dropdown(self.ident, choices)

    def filter(self, infoname):
        self.check_wato_data_update()
        current = html.request.var(self.ident)
        if not current:
            return ""
        path_regex = "^/wato/%s" % current.replace("\n", "")  # prevent insertions attack
        if current.endswith("/"):  # Hosts directly in this folder
            path_regex += "hosts.mk"
        else:
            path_regex += "/"
        if "*" in current:  # used by virtual host tree snapin
            path_regex = path_regex.replace(".", "\\.").replace("*", ".*")
            op = "~~"
        else:
            op = "~"
        return "Filter: host_filename %s %s\n" % (op, path_regex)

    # Construct pair-list of ( folder-path, title ) to be used
    # by the HTML selection box. This also updates self.path_to_tree,
    # a dictionary from the path to the title, by recursively scanning the
    # folders
    def folder_selection(self, folder, depth=0) -> Iterator[Tuple[str, str]]:
        my_path: str = folder.path()
        self.path_to_tree[my_path] = folder.title()

        title_prefix = ("\u00a0" * 6 * depth) + "\u2514\u2500 " if depth else ""

        yield (my_path, title_prefix + folder.title())

        for subfolder in sorted(folder.subfolders(), key=lambda x: x.title().lower()):
            yield from self.folder_selection(subfolder, depth + 1)

    def heading_info(self):
        # FIXME: There is a problem with caching data and changing titles of WATO files
        # Everything is changed correctly but the filter object is stored in the
        # global multisite_filters var and self.path_to_tree is not refreshed when
        # rendering this title. Thus the threads might have old information about the
        # file titles and so on.
        # The call below needs to use some sort of indicator wether the cache needs
        # to be renewed or not.
        self.check_wato_data_update()
        current = html.request.var(self.ident)
        if current and current != "/":
            return self.path_to_tree.get(current)
