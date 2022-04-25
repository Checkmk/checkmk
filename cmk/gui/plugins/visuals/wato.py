#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Dict, Iterator, List, Optional, Set, Tuple

from cmk.utils.prediction import lq_logic

import cmk.gui.site_config as site_config
import cmk.gui.sites as sites
import cmk.gui.watolib as watolib
from cmk.gui.config import active_config
from cmk.gui.htmllib.context import html
from cmk.gui.i18n import _l
from cmk.gui.plugins.visuals.utils import Filter, filter_registry
from cmk.gui.type_defs import Choices, FilterHeader, FilterHTTPVariables
from cmk.gui.valuespec import DualListChoice


def _wato_folders_to_lq_regex(path: str) -> str:
    path_regex = "^/wato/%s" % path.replace("\n", "")  # prevent insertions attack
    if path.endswith("/"):  # Hosts directly in this folder
        path_regex += "hosts.mk"
    else:
        path_regex += "/"

    if "*" in path:  # used by virtual host tree snapin
        path_regex = path_regex.replace(".", "\\.").replace("*", ".*")
        op = "~~"
    else:
        op = "~"
    return "%s %s" % (op, path_regex)


class FilterWatoFolder(Filter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_wato_data_update = None

    def available(self):
        # This filter is also available on slave sites with disabled WATO
        # To determine if this site is a slave we check the existance of the distributed_wato.mk
        # file and the absence of any site configuration
        return active_config.wato_enabled or site_config.is_wato_slave_site()

    def load_wato_data(self):
        self.tree = watolib.Folder.root_folder()
        self.path_to_tree: Dict[str, str] = {}  # will be filled by self.folder_selection
        self.selection = list(self.folder_selection(self.tree))
        self.last_wato_data_update = time.time()

    def check_wato_data_update(self):
        if not self.last_wato_data_update or time.time() - self.last_wato_data_update > 5:
            self.load_wato_data()

    def choices(self) -> Choices:
        self.check_wato_data_update()
        allowed_folders = self._fetch_folders()
        return [entry for entry in self.selection if entry[0] in allowed_folders]

    def _fetch_folders(self) -> Set[str]:
        # Note: WATO Folders that the user has not permissions to must not be visible.
        # Permissions in this case means, that the user has view permissions for at
        # least one host in that folder.
        result = sites.live().query(
            "GET hosts\nCache: reload\nColumns: filename\nStats: state >= 0\n"
        )
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
        return allowed_folders

    def display(self, value: FilterHTTPVariables) -> None:
        html.dropdown(self.ident, self.choices(), deflt=value.get(self.htmlvars[0], ""))

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        self.check_wato_data_update()
        if folder := value.get(self.ident):
            return "Filter: host_filename %s\n" % _wato_folders_to_lq_regex(folder)
        return ""

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

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        # FIXME: There is a problem with caching data and changing titles of WATO files
        # Everything is changed correctly but the filter object is stored in the
        # global multisite_filters var and self.path_to_tree is not refreshed when
        # rendering this title. Thus the threads might have old information about the
        # file titles and so on.
        # The call below needs to use some sort of indicator wether the cache needs
        # to be renewed or not.
        self.check_wato_data_update()
        current = value.get(self.ident)
        if current and current != "/":
            return self.path_to_tree.get(current)
        return None


filter_registry.register(
    FilterWatoFolder(
        ident="wato_folder",
        title=_l("Folder"),
        sort_index=10,
        info="host",
        htmlvars=["wato_folder"],
        link_columns=[],
    ),
)


class FilterMultipleWatoFolder(FilterWatoFolder):
    # Once filters are managed by a valuespec and we get more complex
    # datastuctures beyond FilterHTTPVariable there must be a back&forth
    # for data
    def valuespec(self):
        # Drop Main directory represented by empty string, because it means
        # don't filter after any folder due to recursive folder filtering.
        choices = [(name, folder) for name, folder in self.choices() if name]
        return DualListChoice(choices=choices, rows=4, enlarge_active=True)

    def _to_list(self, value: FilterHTTPVariables) -> List[str]:
        if folders := value.get(self.htmlvars[0], ""):
            return folders.split("|")
        return []

    def display(self, value: FilterHTTPVariables):
        self.valuespec().render_input(self.ident, self._to_list(value))

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        self.check_wato_data_update()
        regex_values = list(map(_wato_folders_to_lq_regex, self._to_list(value)))
        return lq_logic("Filter: host_filename", regex_values, "Or")

    def value(self) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the HTML
        var context. This can be used to persist the filter settings."""
        return {self.htmlvars[0]: "|".join(self.valuespec().from_html_vars(self.ident))}

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        self.check_wato_data_update()
        return ", ".join(
            filter(
                None,
                (
                    self.path_to_tree.get(folder)
                    for folder in self._to_list(value)
                    if folder and folder != "/"
                ),
            )
        )


filter_registry.register(
    FilterMultipleWatoFolder(
        ident="wato_folders",
        title=_l("Multiple WATO Folders"),
        sort_index=20,
        info="host",
        htmlvars=["wato_folders"],
        link_columns=[],
    ),
)
