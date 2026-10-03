#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Iterator
from typing import override

from cmk.gui import site_config, sites
from cmk.gui.config import active_config, RequestCacheConfig
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import ChoiceMapping, ColumnName, FilterHeader, FilterHTTPVariables
from cmk.gui.valuespec import DualListChoice, ValueSpec
from cmk.gui.visuals.filter import Filter, FilterGroup, FilterRegistry
from cmk.gui.visuals.filter.components import Dropdown, DualList, FilterComponent, StaticText
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.livestatus_client import lq_logic
from cmk.web.utils.request_cache import RequestCache
from cmk.web.utils.speaklater import LazyString


def register(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        FilterWatoFolder(
            ident="wato_folder",
            title=_l("Folder"),
            sort_index=10,
            info="host",
            htmlvars=["wato_folder"],
            link_columns=[],
            group=FilterGroup.FOLDER,
        ),
    )

    filter_registry.register(
        FilterMultipleWatoFolder(
            ident="wato_folders",
            title=_l("Multiple Setup Folders"),
            sort_index=20,
            info="host",
            htmlvars=["wato_folders"],
            link_columns=[],
            group=FilterGroup.FOLDER,
        ),
    )


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
    return f"{op} {path_regex}"


def _folder_selection(folder: Folder, depth: int = 0) -> Iterator[tuple[str, str]]:
    """The paths and titles of the folder and all folders below, indented by depth"""
    title_prefix = ("\u00a0" * 6 * depth) + "\u2514\u2500 " if depth else ""

    yield (folder.path(), title_prefix + folder.title())

    for subfolder in sorted(folder.subfolders(), key=lambda x: x.title().lower()):
        yield from _folder_selection(subfolder, depth + 1)


class FilterWatoFolder(Filter):
    def __init__(
        self,
        ident: str,
        title: str | LazyString,
        sort_index: int,
        info: str,
        htmlvars: list[str],
        link_columns: list[ColumnName],
        group: FilterGroup | None = None,
    ) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=htmlvars,
            link_columns=link_columns,
            group=group,
        )

    @override
    def available(self) -> bool:
        # This filter is also available on slave sites with disabled WATO
        # To determine if this site is a slave we check the existance of the distributed_wato.mk
        # file and the absence of any site configuration
        return active_config.wato_enabled or site_config.is_distributed_setup_remote_site(
            active_config.sites
        )

    def choices(self) -> ChoiceMapping:
        allowed_folders = self._fetch_folders()
        return {
            path: title
            for path, title in _folder_selection(folder_tree().root_folder())
            if path in allowed_folders
        }

    def _folder_title(self, path: str) -> str | None:
        folder = folder_tree().all_folders().get(path)
        return None if folder is None else folder.title()

    def _fetch_folders(self) -> set[str]:
        # Note: Setup Folders that the user has not permissions to must not be visible.
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

    @override
    def components(
        self, _request_cache: RequestCache[RequestCacheConfig]
    ) -> Iterable[FilterComponent]:
        yield Dropdown(
            id=self.ident,
            choices=self.choices(),
            default_value="",  # root folder
        )

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if folder := value.get(self.ident):
            return "Filter: host_filename %s\n" % _wato_folders_to_lq_regex(folder)
        return ""

    @override
    def heading_info(
        self, value: FilterHTTPVariables, _request_cache: RequestCache[RequestCacheConfig]
    ) -> str | None:
        current = value.get(self.ident)
        if current and current != "/":
            return self._folder_title(current)
        return None


class FilterMultipleWatoFolder(FilterWatoFolder):
    # Once filters are managed by a valuespec and we get more complex
    # datastuctures beyond FilterHTTPVariable there must be a back&forth
    # for data
    def valuespec(self) -> ValueSpec:
        choices = [(name, folder) for name, folder in self.choices().items()]
        return DualListChoice(choices=choices, rows=4, enlarge_active=True)

    def _to_list(self, value: FilterHTTPVariables) -> list[str]:
        if folders := value.get(self.htmlvars[0], ""):
            return folders.split("|")
        return []

    @override
    def choices(self) -> ChoiceMapping:
        # Drop Main directory represented by empty string, because it means
        # don't filter after any folder due to recursive folder filtering.
        return {name: folder for name, folder in super().choices().items() if name}

    @override
    def components(
        self, _request_cache: RequestCache[RequestCacheConfig]
    ) -> Iterable[FilterComponent]:
        if choices := self.choices():
            yield DualList(
                id=self.ident,
                choices=choices,
            )
        else:
            yield StaticText(text=_("There are no elements for selection."))

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        regex_values = list(map(_wato_folders_to_lq_regex, self._to_list(value)))
        return lq_logic("Filter: host_filename", regex_values, "Or")

    @override
    def value(self, _request_cache: RequestCache[RequestCacheConfig]) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the HTML
        var context. This can be used to persist the filter settings."""
        return {self.htmlvars[0]: "|".join(self.valuespec().from_html_vars(self.ident))}

    @override
    def heading_info(
        self, value: FilterHTTPVariables, _request_cache: RequestCache[RequestCacheConfig]
    ) -> str | None:
        return ", ".join(
            filter(
                None,
                (
                    self._folder_title(folder)
                    for folder in self._to_list(value)
                    if folder and folder != "/"
                ),
            )
        )
