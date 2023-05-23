#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
import json
import os
import shutil
import time
import xml.dom.minidom
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import auto, Enum
from pathlib import Path
from typing import Literal, NamedTuple, TypedDict

import dicttoxml  # type: ignore[import]

import livestatus

import cmk.utils.paths
import cmk.utils.regex
import cmk.utils.store as store
from cmk.utils.exceptions import MKException, MKGeneralException
from cmk.utils.structured_data import (
    DeltaStructuredDataNode,
    ImmutableDeltaTree,
    ImmutableTree,
    load_tree,
    make_filter_from_choice,
    parse_visible_raw_path,
    SDFilter,
    SDFilterFunc,
    SDKey,
    SDPath,
    StructuredDataNode,
)
from cmk.utils.type_defs import HostName

import cmk.gui.pages
import cmk.gui.sites as sites
import cmk.gui.userdb as userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Row
from cmk.gui.valuespec import TextInput, ValueSpec

# TODO Cleanup variation:
#   - InventoryPath.parse parses NOT visible, internal tree paths used in displayhints/views
#   - cmk.utils.structured_data.py::parse_visible_raw_path
#     parses visible, internal tree paths for contact groups etc.
# => Should be unified one day.


class TreeSource(Enum):
    node = auto()
    table = auto()
    attributes = auto()


@dataclass(frozen=True)
class InventoryPath:
    path: SDPath
    source: TreeSource
    key: SDKey | None = None

    @classmethod
    def parse(cls, raw_path: str) -> InventoryPath:
        if not raw_path:
            return InventoryPath(
                path=tuple(),
                source=TreeSource.node,
            )

        if raw_path.endswith("."):
            path = raw_path[:-1].strip(".").split(".")
            return InventoryPath(
                path=cls._sanitize_path(raw_path[:-1].strip(".").split(".")),
                source=TreeSource.node,
            )

        if raw_path.endswith(":"):
            return InventoryPath(
                path=cls._sanitize_path(raw_path[:-1].strip(".").split(".")),
                source=TreeSource.table,
            )

        path = raw_path.strip(".").split(".")
        sanitized_path = cls._sanitize_path(path[:-1])
        if ":" in path[-2]:
            source = TreeSource.table
            # Forget the last '*' or an index like '17'
            # because it's related to columns (not nodes)
            sanitized_path = sanitized_path[:-1]
        else:
            source = TreeSource.attributes

        return InventoryPath(
            path=sanitized_path,
            source=source,
            key=path[-1],
        )

    @staticmethod
    def _sanitize_path(path: Sequence[str]) -> SDPath:
        # ":": Nested tables, see also lib/structured_data.py
        return tuple(p for part in path for p in (part.split(":") if ":" in part else [part]) if p)

    @property
    def node_name(self) -> str:
        return self.path[-1] if self.path else ""


class _PermittedPath(TypedDict):
    visible_raw_path: str


class PermittedPath(_PermittedPath, total=False):
    attributes: tuple[str, Sequence[str]] | Literal["nothing"]
    columns: tuple[str, Sequence[str]] | Literal["nothing"]
    nodes: tuple[str, Sequence[str]] | Literal["nothing"]


def _make_filters_from_permitted_paths(
    permitted_paths: Sequence[PermittedPath],
) -> Sequence[SDFilter]:
    def _make_filter(entry: PermittedPath) -> SDFilter:
        return SDFilter(
            path=parse_visible_raw_path(entry["visible_raw_path"]),
            filter_attributes=make_filter_from_choice(entry.get("attributes")),
            filter_columns=make_filter_from_choice(entry.get("columns")),
            filter_nodes=make_filter_from_choice(entry.get("nodes")),
        )

    return [_make_filter(entry) for entry in permitted_paths if entry]


def load_filtered_and_merged_tree(row: Row) -> ImmutableTree | None:
    """Load inventory tree from file, status data tree from row,
    merge these trees and returns the filtered tree"""
    host_name = row.get("host_name")
    inventory_tree = _load_tree_from_file(tree_type="inventory", host_name=host_name)
    status_data_tree: ImmutableTree | None
    if raw_status_data_tree := row.get("host_structured_status"):
        status_data_tree = ImmutableTree(
            StructuredDataNode.deserialize(ast.literal_eval(raw_status_data_tree.decode("utf-8")))
        )
    else:
        status_data_tree = _load_tree_from_file(tree_type="status_data", host_name=host_name)

    if inventory_tree is None:
        return status_data_tree

    if status_data_tree is None:
        return inventory_tree

    merged_tree = inventory_tree.merge(status_data_tree)
    if isinstance(permitted_paths := _get_permitted_inventory_paths(), list):
        return merged_tree.filter(_make_filters_from_permitted_paths(permitted_paths))

    return merged_tree


def get_status_data_via_livestatus(site: livestatus.SiteId | None, hostname: HostName) -> Row:
    query = (
        "GET hosts\nColumns: host_structured_status\nFilter: host_name = %s\n"
        % livestatus.lqencode(hostname)
    )
    try:
        sites.live().set_only_sites([site] if site else None)
        result = sites.live().query(query)
    finally:
        sites.live().set_only_sites()

    row = {"host_name": hostname}
    if result and result[0]:
        row["host_structured_status"] = result[0][0]
    return row


def get_short_inventory_filepath(hostname: HostName) -> Path:
    return (
        Path(cmk.utils.paths.inventory_output_dir)
        .joinpath(hostname)
        .relative_to(cmk.utils.paths.omd_root)
    )


def vs_element_inventory_visible_raw_path() -> tuple[str, ValueSpec]:
    # Via 'Display options::Show internal tree paths' the tree paths are shown as 'path.to.node'.
    # We keep this format in order to easily copy&paste these tree paths to
    # 'Contact groups::Permitted HW/SW inventory paths'.
    return (
        "visible_raw_path",
        TextInput(
            title=_("Path to categories"),
            size=60,
            allow_empty=False,
        ),
    )


def vs_inventory_path_or_keys_help():
    return _(
        "Via <tt>Display options > Show internal tree paths</tt>"
        " on the HW/SW Inventory page of a host the internal tree paths leading"
        " to subcategories, the keys of singles values or table column names"
        " become visible. Key columns of tables are marked with '*'. See"
        ' <a href="https://docs.checkmk.com/latest/de/inventory.html">HW/SW Inventory</a>.'
        " for more details about the HW/SW Inventory system."
    )


# .
#   .--history-------------------------------------------------------------.
#   |                   _     _     _                                      |
#   |                  | |__ (_)___| |_ ___  _ __ _   _                    |
#   |                  | '_ \| / __| __/ _ \| '__| | | |                   |
#   |                  | | | | \__ \ || (_) | |  | |_| |                   |
#   |                  |_| |_|_|___/\__\___/|_|   \__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


_DEFAULT_PATH_TO_TREE = Path()


class InventoryHistoryPath(NamedTuple):
    path: Path
    timestamp: int | None

    @classmethod
    def default(cls) -> InventoryHistoryPath:
        return InventoryHistoryPath(
            path=_DEFAULT_PATH_TO_TREE,
            timestamp=None,
        )

    @property
    def short(self) -> Path:
        return self.path.relative_to(cmk.utils.paths.omd_root)


class HistoryEntry(NamedTuple):
    timestamp: int | None
    new: int
    changed: int
    removed: int
    delta_tree: ImmutableDeltaTree


class FilteredInventoryHistoryPaths(NamedTuple):
    start_tree_path: InventoryHistoryPath
    tree_paths: Sequence[InventoryHistoryPath]


class FilterInventoryHistoryPathsError(Exception):
    pass


def load_latest_delta_tree(hostname: HostName) -> ImmutableDeltaTree | None:
    def _get_latest_timestamps(
        tree_paths: Sequence[InventoryHistoryPath],
    ) -> FilteredInventoryHistoryPaths:
        if len(tree_paths) == 0:
            raise FilterInventoryHistoryPathsError()
        return FilteredInventoryHistoryPaths(
            start_tree_path=(
                InventoryHistoryPath.default() if len(tree_paths) == 1 else tree_paths[-2]
            ),
            tree_paths=[tree_paths[-1]],
        )

    delta_history, _corrupted_history_files = _get_history(
        hostname,
        filter_tree_paths=_get_latest_timestamps,
    )
    if not delta_history:
        return None
    return delta_history[0].delta_tree


def load_delta_tree(
    hostname: HostName,
    timestamp: int,
) -> tuple[ImmutableDeltaTree | None, Sequence[str]]:
    """Load inventory history and compute delta tree of a specific timestamp"""
    # Timestamp is timestamp of the younger of both trees. For the oldest
    # tree we will just return the complete tree - without any delta
    # computation.

    def _search_timestamps(
        tree_paths: Sequence[InventoryHistoryPath], timestamp: int
    ) -> FilteredInventoryHistoryPaths:
        for idx, tree_path in enumerate(tree_paths):
            if tree_path.timestamp == timestamp:
                if idx == 0:
                    return FilteredInventoryHistoryPaths(
                        start_tree_path=InventoryHistoryPath.default(),
                        tree_paths=[tree_path],
                    )
                return FilteredInventoryHistoryPaths(
                    start_tree_path=tree_paths[idx - 1],
                    tree_paths=[tree_path],
                )
        raise MKGeneralException(
            _("Found no history entry at the time of '%s' for the host '%s'")
            % (timestamp, hostname)
        )

    delta_history, corrupted_history_files = _get_history(
        hostname,
        filter_tree_paths=lambda filter_tree_paths: _search_timestamps(
            filter_tree_paths, timestamp
        ),
    )
    if not delta_history:
        return None, []
    return delta_history[0].delta_tree, corrupted_history_files


def get_history(hostname: HostName) -> tuple[Sequence[HistoryEntry], Sequence[str]]:
    return _get_history(
        hostname,
        filter_tree_paths=lambda tree_paths: FilteredInventoryHistoryPaths(
            start_tree_path=InventoryHistoryPath.default(),
            tree_paths=tree_paths,
        ),
    )


def _get_history(
    hostname: HostName,
    *,
    filter_tree_paths: Callable[[Sequence[InventoryHistoryPath]], FilteredInventoryHistoryPaths],
) -> tuple[Sequence[HistoryEntry], Sequence[str]]:
    if "/" in hostname:
        return [], []  # just for security reasons

    if not (tree_paths := _get_inventory_history_paths(hostname)):
        return [], []

    try:
        filtered_tree_paths = filter_tree_paths(tree_paths)
    except FilterInventoryHistoryPathsError:
        return [], []

    cached_tree_loader = _CachedTreeLoader()
    corrupted_history_files: set[Path] = set()
    history: list[HistoryEntry] = []
    filters = (
        _make_filters_from_permitted_paths(permitted_paths)
        if isinstance(permitted_paths := _get_permitted_inventory_paths(), list)
        else None
    )

    for previous, current in _get_pairs(filtered_tree_paths):
        if current.timestamp is None:
            continue

        cached_delta_tree_loader = _CachedDeltaTreeLoader(
            hostname,
            previous.timestamp,
            current.timestamp,
            filters,
        )

        if (cached_history_entry := cached_delta_tree_loader.get_cached_entry()) is not None:
            history.append(cached_history_entry)
            continue

        try:
            previous_tree = cached_tree_loader.get_tree(previous.path)
            current_tree = cached_tree_loader.get_tree(current.path)
        except LoadStructuredDataError:
            corrupted_history_files.add(current.short)
            continue

        if (
            history_entry := cached_delta_tree_loader.get_calculated_or_store_entry(
                previous_tree, current_tree
            )
        ) is not None:
            history.append(history_entry)

    return history, sorted([str(path) for path in corrupted_history_files])


def _get_inventory_history_paths(hostname: HostName) -> Sequence[InventoryHistoryPath]:
    inventory_path = Path(cmk.utils.paths.inventory_output_dir, hostname)
    inventory_archive_dir = Path(cmk.utils.paths.inventory_archive_dir, hostname)

    try:
        archived_tree_paths = [
            InventoryHistoryPath(
                path=filepath,
                timestamp=int(filepath.name),
            )
            for filepath in sorted(inventory_archive_dir.iterdir())
        ]
    except FileNotFoundError:
        return []

    try:
        archived_tree_paths.append(
            InventoryHistoryPath(
                path=inventory_path,
                timestamp=int(inventory_path.stat().st_mtime),
            )
        )
    except FileNotFoundError:
        pass

    return archived_tree_paths


def _get_pairs(
    filtered_tree_paths: FilteredInventoryHistoryPaths,
) -> Sequence[tuple[InventoryHistoryPath, InventoryHistoryPath]]:
    start_tree_path = filtered_tree_paths.start_tree_path

    pairs: list[tuple[InventoryHistoryPath, InventoryHistoryPath]] = []
    for tree_path in filtered_tree_paths.tree_paths:
        pairs.append((start_tree_path, tree_path))
        start_tree_path = tree_path

    return pairs


@dataclass(frozen=True)
class _CachedTreeLoader:
    _lookup: dict[Path, ImmutableTree] = field(default_factory=dict)

    def get_tree(self, filepath: Path) -> ImmutableTree:
        if filepath == _DEFAULT_PATH_TO_TREE:
            return ImmutableTree()

        if filepath in self._lookup:
            return self._lookup[filepath]

        return self._lookup.setdefault(filepath, self._load_tree_from_file(filepath))

    def _load_tree_from_file(self, filepath: Path) -> ImmutableTree:
        try:
            tree = load_tree(filepath)
        except FileNotFoundError:
            raise LoadStructuredDataError()

        if not tree:
            # load_file may return an empty tree
            raise LoadStructuredDataError()

        return tree


@dataclass(frozen=True)
class _CachedDeltaTreeLoader:
    hostname: HostName
    previous_timestamp: int | None
    current_timestamp: int
    # TODO Cleanup
    filters: Sequence[SDFilter] | None

    @property
    def _path(self) -> Path:
        return Path(
            cmk.utils.paths.inventory_delta_cache_dir,
            self.hostname,
            f"{self.previous_timestamp}_{self.current_timestamp}",
        )

    def get_cached_entry(self) -> HistoryEntry | None:
        try:
            cached_data = store.load_object_from_file(self._path, default=None)
        except MKGeneralException:
            return None

        if cached_data is None:
            return None

        new, changed, removed, raw_delta_tree = cached_data
        return self._make_history_entry(
            new,
            changed,
            removed,
            ImmutableDeltaTree(DeltaStructuredDataNode.deserialize(raw_delta_tree)),
        )

    def get_calculated_or_store_entry(
        self,
        previous_tree: ImmutableTree,
        current_tree: ImmutableTree,
    ) -> HistoryEntry | None:
        delta_tree = current_tree.difference(previous_tree)
        delta_result = delta_tree.tree.count_entries()
        new = delta_result["new"]
        changed = delta_result["changed"]
        removed = delta_result["removed"]
        if new or changed or removed:
            store.save_text_to_file(
                self._path,
                repr((new, changed, removed, delta_tree.tree.serialize())),
            )
            return self._make_history_entry(new, changed, removed, delta_tree)
        return None

    def _make_history_entry(
        self, new: int, changed: int, removed: int, delta_tree: ImmutableDeltaTree
    ) -> HistoryEntry | None:
        if self.filters is None:
            return HistoryEntry(self.current_timestamp, new, changed, removed, delta_tree)

        if not (filtered_delta_tree := delta_tree.filter(self.filters)):
            return None

        delta_result = filtered_delta_tree.tree.count_entries()
        return HistoryEntry(
            self.current_timestamp,
            delta_result["new"],
            delta_result["changed"],
            delta_result["removed"],
            filtered_delta_tree,
        )


# .
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


class LoadStructuredDataError(MKException):
    pass


@request_memoize(maxsize=None)
def _load_tree_from_file(
    *, tree_type: Literal["inventory", "status_data"], host_name: HostName | None
) -> ImmutableTree | None:
    """Load data of a host, cache it in the current HTTP request"""
    if not host_name:
        return None

    if "/" in host_name:
        # just for security reasons
        return None

    try:
        return load_tree(
            Path(
                cmk.utils.paths.inventory_output_dir
                if tree_type == "inventory"
                else cmk.utils.paths.status_data_dir
            )
            / host_name
        )
    except Exception as e:
        if active_config.debug:
            html.show_warning("%s" % e)
        raise LoadStructuredDataError()


@request_memoize()
def _get_permitted_inventory_paths() -> Sequence[PermittedPath] | None:
    """
    Returns either a list of permitted paths or
    None in case the user is allowed to see the whole tree.
    """

    user_groups = [] if user.id is None else userdb.contactgroups_of_user(user.id)

    if not user_groups:
        return None

    forbid_whole_tree = False
    permitted_paths = []
    for user_group in user_groups:
        inventory_paths = active_config.multisite_contactgroups.get(user_group, {}).get(
            "inventory_paths"
        )
        if inventory_paths is None:
            # Old configuration: no paths configured means 'allow_all'
            return None

        if inventory_paths == "allow_all":
            return None

        if inventory_paths == "forbid_all":
            forbid_whole_tree = True
            continue

        permitted_paths.extend(inventory_paths[1])

    if forbid_whole_tree and not permitted_paths:
        return []

    return permitted_paths


# .
#   .--Inventory API-------------------------------------------------------.
#   |   ___                      _                        _    ____ ___    |
#   |  |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _     / \  |  _ \_ _|   |
#   |   | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |   / _ \ | |_) | |    |
#   |   | || | | \ V /  __/ | | | || (_) | |  | |_| |  / ___ \|  __/| |    |
#   |  |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, | /_/   \_\_|  |___|   |
#   |                                          |___/                       |
#   '----------------------------------------------------------------------'


def check_for_valid_hostname(hostname: HostName) -> None:
    """test hostname for invalid chars, raises MKUserError if invalid chars are found
    >>> check_for_valid_hostname("klappspaten")
    >>> check_for_valid_hostname("../../etc/passwd")
    Traceback (most recent call last):
    cmk.gui.exceptions.MKUserError: You need to provide a valid "hostname". Only letters, digits, dash, underscore and dot are allowed.
    """
    hostname_regex = cmk.utils.regex.regex(cmk.utils.regex.REGEX_HOST_NAME)
    if hostname_regex.match(str(hostname)):
        return
    raise MKUserError(
        None,
        _(
            'You need to provide a valid "hostname". '
            "Only letters, digits, dash, underscore and dot are allowed.",
        ),
    )


@cmk.gui.pages.register("host_inv_api")
def page_host_inv_api() -> None:
    # The response is always a top level dict with two elements:
    # a) result_code - This is 0 for expected processing and 1 for an error
    # b) result      - In case of an error this is the error message, a UTF-8 encoded string.
    #                  In case of success this is a dictionary containing the host inventory.
    try:
        api_request = request.get_request()
        # The user can either specify a single host or provide a list of host names. In case
        # multiple hosts are handled, there is a top level dict added with "host > invdict" pairs
        hosts = api_request.get("hosts")
        if hosts:
            result = {}
            for a_host_name in hosts:
                check_for_valid_hostname(a_host_name)
                result[a_host_name] = inventory_of_host(a_host_name, api_request)

        else:
            host_name = api_request.get("host")
            if host_name is None:
                raise MKUserError("host", _('You need to provide a "host".'))
            check_for_valid_hostname(host_name)

            result = inventory_of_host(host_name, api_request)

            if not result and not has_inventory(host_name):
                raise MKGeneralException(_("Found no inventory data for this host."))

        resp = {"result_code": 0, "result": result}

    except MKException as e:
        resp = {"result_code": 1, "result": "%s" % e}

    except Exception as e:
        if active_config.debug:
            raise
        resp = {"result_code": 1, "result": "%s" % e}

    if html.output_format == "json":
        _write_json(resp)
    elif html.output_format == "xml":
        _write_xml(resp)
    else:
        _write_python(resp)


def has_inventory(hostname: HostName) -> bool:
    return (
        os.path.exists(f"{cmk.utils.paths.inventory_output_dir}/{hostname}") if hostname else False
    )


def _make_filters_from_api_request_paths(api_request_paths: Sequence[str]) -> Sequence[SDFilter]:
    def _make_choices_filter(choices: Sequence[str | int]) -> SDFilterFunc:
        return lambda key: key in choices

    def _make_filter(entry: tuple[SDPath, Sequence[str] | None]) -> SDFilter:
        path, keys = entry
        if keys is None:
            return SDFilter(
                path=path,
                filter_nodes=lambda k: True,
                filter_attributes=lambda k: True,
                filter_columns=lambda k: True,
            )
        return SDFilter(
            path=path,
            filter_nodes=lambda k: False,
            filter_attributes=_make_choices_filter(keys),
            filter_columns=_make_choices_filter(keys),
        )

    return [
        _make_filter((inventory_path.path, [inventory_path.key] if inventory_path.key else None))
        for raw_path in api_request_paths
        for inventory_path in (InventoryPath.parse(raw_path),)
    ]


def inventory_of_host(host_name: HostName, api_request):  # type: ignore[no-untyped-def]
    raw_site = api_request.get("site")
    site = livestatus.SiteId(raw_site) if raw_site is not None else None
    verify_permission(host_name, site)

    row = get_status_data_via_livestatus(site, host_name)
    if (tree := load_filtered_and_merged_tree(row)) is None:
        return {}

    if "paths" in api_request:
        return tree.filter(
            _make_filters_from_api_request_paths(api_request["paths"])
        ).tree.serialize()

    return tree.tree.serialize()


def verify_permission(host_name: HostName, site: livestatus.SiteId | None) -> None:
    if user.may("general.see_all"):
        return

    query = "GET hosts\nFilter: host_name = {}\nStats: state >= 0{}".format(
        livestatus.lqencode(host_name),
        "\nAuthUser: %s" % livestatus.lqencode(user.id) if user.id else "",
    )

    if site:
        sites.live().set_only_sites([site])

    try:
        result = sites.live().query_summed_stats(query, "ColumnHeaders: off\n")
    except livestatus.MKLivestatusNotFoundError:
        raise MKAuthException(
            _("No such inventory tree of host %s. You may also have no access to this host.")
            % host_name
        )
    finally:
        if site:
            sites.live().set_only_sites()

    if result[0] == 0:
        raise MKAuthException(_("You are not allowed to access the host %s.") % host_name)


def _write_xml(resp):
    unformated_xml = dicttoxml.dicttoxml(resp)
    dom = xml.dom.minidom.parseString(unformated_xml)
    response.set_data(dom.toprettyxml())


def _write_json(resp):
    response.set_data(json.dumps(resp, sort_keys=True, indent=4, separators=(",", ": ")))


def _write_python(resp):
    response.set_data(repr(resp))


class InventoryHousekeeping:
    def __init__(self) -> None:
        super().__init__()
        self._inventory_path = Path(cmk.utils.paths.inventory_output_dir)
        self._inventory_archive_path = Path(cmk.utils.paths.inventory_archive_dir)
        self._inventory_delta_cache_path = Path(cmk.utils.paths.inventory_delta_cache_dir)

    def run(self):
        if (
            not self._inventory_delta_cache_path.exists()
            or not self._inventory_archive_path.exists()
        ):
            return

        last_cleanup = self._inventory_delta_cache_path / "last_cleanup"
        # TODO: remove with pylint 2
        if last_cleanup.exists() and time.time() - last_cleanup.stat().st_mtime < 3600 * 12:
            return

        # TODO: remove with pylint 2
        inventory_archive_hosts = {
            x.name for x in self._inventory_archive_path.iterdir() if x.is_dir()
        }
        inventory_delta_cache_hosts = {
            x.name for x in self._inventory_delta_cache_path.iterdir() if x.is_dir()
        }

        folders_to_delete = inventory_delta_cache_hosts - inventory_archive_hosts
        for foldername in folders_to_delete:
            shutil.rmtree(str(self._inventory_delta_cache_path / foldername))

        inventory_delta_cache_hosts -= folders_to_delete
        for hostname in inventory_delta_cache_hosts:
            available_timestamps = self._get_timestamps_for_host(hostname)
            for filename in [
                x.name
                for x in (self._inventory_delta_cache_path / hostname).iterdir()
                if not x.is_dir()
            ]:
                delete = False
                try:
                    first, second = filename.split("_")
                    if first not in available_timestamps or second not in available_timestamps:
                        delete = True
                except ValueError:
                    delete = True
                if delete:
                    (self._inventory_delta_cache_path / hostname / filename).unlink()

        # TODO: remove with pylint 2
        last_cleanup.touch()

    def _get_timestamps_for_host(self, hostname):
        timestamps = {"None"}  # 'None' refers to the histories start
        try:
            timestamps.add("%d" % (self._inventory_path / hostname).stat().st_mtime)
        except OSError:
            pass

        for filename in [
            x for x in (self._inventory_archive_path / hostname).iterdir() if not x.is_dir()
        ]:
            timestamps.add(filename.name)
        return timestamps


def execute_inventory_housekeeping_job() -> None:
    cmk.gui.inventory.InventoryHousekeeping().run()
