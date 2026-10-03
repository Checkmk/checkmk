#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.watolib.hosts_and_folders import (
    FolderTree,
    FolderTreeConfigSource,
    HostsAndFoldersConfig,
)
from cmk.web.utils.html import HTML
from cmk.web.utils.request_cache import CacheKey


class FolderTitles:
    """The titles of the folders shown by a request

    The folder tree is built on the first lookup, and each folder is resolved once. A request
    showing no folder builds no tree. The titles are a snapshot: a request editing a folder keeps
    showing the titles it resolved first.
    """

    def __init__(self, config: FolderTreeConfigSource) -> None:
        self._tree_config = HostsAndFoldersConfig.from_config(config)
        self._tree: FolderTree | None = None
        self._title_paths: dict[tuple[str, bool], list[str] | list[HTML] | str] = {}

    def _folder_tree(self) -> FolderTree:
        if self._tree is None:
            self._tree = FolderTree(config=self._tree_config)
        return self._tree

    def title_path(self, wato_path: str, with_links: bool) -> list[str] | list[HTML] | str:
        """The titles from the main folder down to the folder, or the error resolving them"""
        if (key := (wato_path, with_links)) not in self._title_paths:
            self._title_paths[key] = self._resolve_title_path(wato_path, with_links)
        return self._title_paths[key]

    def _resolve_title_path(self, wato_path: str, with_links: bool) -> list[str] | list[HTML] | str:
        try:
            folder = self._folder_tree().folder(wato_path)
            return folder.title_path_with_links() if with_links else folder.title_path()
        except MKGeneralException:
            # happens when a path can not be resolved using the local Setup.
            # e.g. when having an independent site with different folder
            # hierarchy added to the GUI.
            # Display the raw path rather than the exception text.
            return wato_path.split("/")
        except Exception as e:
            return "%s" % e


FOLDER_TITLES = CacheKey("folder_titles", FolderTitles)
