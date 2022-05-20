#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
import json
import os
import shutil
import time
import xml.dom.minidom  # type: ignore[import]
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Literal, NamedTuple, Optional, Sequence, Set, Tuple, Union

import dicttoxml  # type: ignore[import]

import livestatus

import cmk.utils.paths
import cmk.utils.regex
import cmk.utils.store as store
from cmk.utils.exceptions import MKException, MKGeneralException
from cmk.utils.structured_data import (
    make_filter,
    SDKeys,
    SDPath,
    SDRawPath,
    SDRow,
    StructuredDataNode,
    StructuredDataStore,
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
#   - parse_tree_path parses NOT visible, internal tree paths used in displayhints/views
#   - cmk.utils.structured_data.py::parse_visible_raw_path
#     parses visible, internal tree paths for contact groups etc.
# => Should be unified one day.

InventoryValue = Union[None, str, int, float]
InventoryRows = List[SDRow]


def get_inventory_table(tree: StructuredDataNode, raw_path: SDRawPath) -> Optional[InventoryRows]:
    parsed_path, attribute_keys = parse_tree_path(raw_path)
    if attribute_keys != []:
        return None
    table = tree.get_table(parsed_path)
    return None if table is None else table.rows


def get_inventory_attribute(tree: StructuredDataNode, raw_path: SDRawPath) -> InventoryValue:
    parsed_path, attribute_keys = parse_tree_path(raw_path)
    if not attribute_keys:
        return None
    attributes = tree.get_attributes(parsed_path)
    return None if attributes is None else attributes.pairs.get(attribute_keys[-1])


def parse_tree_path(raw_path: SDRawPath) -> Tuple[SDPath, Optional[SDKeys]]:
    # raw_path may look like:
    # .                          (ROOT) => path = []                            key = None
    # .hardware.                 (dict) => path = ["hardware"],                 key = None
    # .hardware.cpu.model        (leaf) => path = ["hardware", "cpu"],          key = "model"
    # .hardware.cpu.             (dict) => path = ["hardware", "cpu"],          key = None
    # .software.packages:17.name (leaf) => path = ["software", "packages", "17"], key = "name"
    # .software.packages:        (list) => path = ["software", "packages"],     key = []
    if not raw_path:
        return [], None

    path: List[str]
    attribute_keys: Optional[SDKeys]

    if raw_path.endswith(":"):
        path = raw_path[:-1].strip(".").split(".")
        attribute_keys = []
    elif raw_path.endswith("."):
        path = raw_path[:-1].strip(".").split(".")
        attribute_keys = None
    else:
        path = raw_path.strip(".").split(".")
        attribute_keys = [path.pop(-1)]

    # ":": Nested tables, see also lib/structured_data.py
    return (
        [p for part in path for p in (part.split(":") if ":" in part else [part]) if p],
        attribute_keys,
    )


def load_filtered_and_merged_tree(row: Row) -> Optional[StructuredDataNode]:
    """Load inventory tree from file, status data tree from row,
    merge these trees and returns the filtered tree"""
    hostname = row.get("host_name")
    inventory_tree = _load_structured_data_tree("inventory", hostname)
    status_data_tree = _load_status_data_tree(hostname, row)

    merged_tree = _merge_inventory_and_status_data_tree(inventory_tree, status_data_tree)
    return _filter_tree(merged_tree)


def get_status_data_via_livestatus(site: Optional[livestatus.SiteId], hostname: HostName) -> Row:
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


def vs_element_inventory_visible_raw_path() -> Tuple[str, ValueSpec]:
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


class TreePath(NamedTuple):
    path: Path
    timestamp: Optional[int]

    @classmethod
    def default(cls) -> TreePath:
        return TreePath(
            path=_DEFAULT_PATH_TO_TREE,
            timestamp=None,
        )

    @property
    def short(self) -> Path:
        return self.path.relative_to(cmk.utils.paths.omd_root)


class HistoryEntry(NamedTuple):
    timestamp: Optional[int]
    new: int
    changed: int
    removed: int
    delta_tree: StructuredDataNode


class FilteredTreePaths(NamedTuple):
    start_tree_path: TreePath
    tree_paths: Sequence[TreePath]


class FilterTreePathsError(Exception):
    pass


def load_latest_delta_tree(hostname: HostName) -> Optional[StructuredDataNode]:
    def _get_latest_timestamps(tree_paths: Sequence[TreePath]) -> FilteredTreePaths:
        if len(tree_paths) == 0:
            raise FilterTreePathsError()
        return FilteredTreePaths(
            start_tree_path=TreePath.default() if len(tree_paths) == 1 else tree_paths[-2],
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
) -> Tuple[Optional[StructuredDataNode], Sequence[str]]:
    """Load inventory history and compute delta tree of a specific timestamp"""
    # Timestamp is timestamp of the younger of both trees. For the oldest
    # tree we will just return the complete tree - without any delta
    # computation.

    def _search_timestamps(tree_paths: Sequence[TreePath], timestamp: int) -> FilteredTreePaths:
        for idx, tree_path in enumerate(tree_paths):
            if tree_path.timestamp == timestamp:
                if idx == 0:
                    return FilteredTreePaths(
                        start_tree_path=TreePath.default(),
                        tree_paths=[tree_path],
                    )
                return FilteredTreePaths(
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


def get_history(hostname: HostName) -> Tuple[Sequence[HistoryEntry], Sequence[str]]:
    return _get_history(
        hostname,
        filter_tree_paths=lambda tree_paths: FilteredTreePaths(
            start_tree_path=TreePath.default(),
            tree_paths=tree_paths,
        ),
    )


def _get_history(
    hostname: HostName,
    *,
    filter_tree_paths: Callable[[Sequence[TreePath]], FilteredTreePaths],
) -> Tuple[Sequence[HistoryEntry], Sequence[str]]:
    if "/" in hostname:
        return [], []  # just for security reasons

    if not (tree_paths := _get_tree_paths(hostname)):
        return [], []

    try:
        filtered_tree_paths = filter_tree_paths(tree_paths)
    except FilterTreePathsError:
        return [], []

    cached_tree_loader = _CachedTreeLoader()
    corrupted_history_files: Set[Path] = set()
    history: List[HistoryEntry] = []

    for previous, current in _get_pairs(filtered_tree_paths):
        if current.timestamp is None:
            continue

        cached_delta_tree_loader = _CachedDeltaTreeLoader(
            hostname,
            previous.timestamp,
            current.timestamp,
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


def _get_tree_paths(hostname: HostName) -> Sequence[TreePath]:
    inventory_path = Path(cmk.utils.paths.inventory_output_dir, hostname)
    inventory_archive_dir = Path(cmk.utils.paths.inventory_archive_dir, hostname)

    try:
        archived_tree_paths = [
            TreePath(
                path=filepath,
                timestamp=int(filepath.name),
            )
            for filepath in sorted(inventory_archive_dir.iterdir())
        ]
    except FileNotFoundError:
        return []

    try:
        archived_tree_paths.append(
            TreePath(
                path=inventory_path,
                timestamp=int(inventory_path.stat().st_mtime),
            )
        )
    except FileNotFoundError:
        pass

    return archived_tree_paths


def _get_pairs(filtered_tree_paths: FilteredTreePaths) -> Sequence[Tuple[TreePath, TreePath]]:
    start_tree_path = filtered_tree_paths.start_tree_path

    pairs: List[Tuple[TreePath, TreePath]] = []
    for tree_path in filtered_tree_paths.tree_paths:
        pairs.append((start_tree_path, tree_path))
        start_tree_path = tree_path

    return pairs


@dataclass(frozen=True)
class _CachedTreeLoader:
    _lookup: Dict[Path, StructuredDataNode] = field(default_factory=dict)

    def get_tree(self, filepath: Path) -> StructuredDataNode:
        if filepath == _DEFAULT_PATH_TO_TREE:
            return StructuredDataNode()

        if filepath in self._lookup:
            return self._lookup[filepath]

        return self._lookup.setdefault(filepath, self._load_tree_from_file(filepath))

    def _load_tree_from_file(self, filepath: Path) -> StructuredDataNode:
        try:
            tree = _filter_tree(StructuredDataStore.load_file(filepath))
        except FileNotFoundError:
            raise LoadStructuredDataError()

        if tree is None or tree.is_empty():
            # load_file may return an empty tree
            raise LoadStructuredDataError()

        return tree


@dataclass(frozen=True)
class _CachedDeltaTreeLoader:
    hostname: HostName
    previous_timestamp: Optional[int]
    current_timestamp: int

    @property
    def _path(self) -> Path:
        return Path(
            cmk.utils.paths.inventory_delta_cache_dir,
            self.hostname,
            "%s_%s" % (self.previous_timestamp, self.current_timestamp),
        )

    def get_cached_entry(self) -> Optional[HistoryEntry]:
        try:
            cached_data = store.load_object_from_file(self._path, default=None)
        except MKGeneralException:
            return None

        if cached_data is None:
            return None

        new, changed, removed, delta_tree_data = cached_data
        delta_tree = StructuredDataNode.deserialize(delta_tree_data)
        return HistoryEntry(self.current_timestamp, new, changed, removed, delta_tree)

    def get_calculated_or_store_entry(
        self,
        previous_tree: StructuredDataNode,
        current_tree: StructuredDataNode,
    ) -> Optional[HistoryEntry]:
        delta_result = current_tree.compare_with(previous_tree)
        new, changed, removed, delta_tree = (
            delta_result.counter["new"],
            delta_result.counter["changed"],
            delta_result.counter["removed"],
            delta_result.delta,
        )
        if new or changed or removed:
            store.save_text_to_file(
                self._path,
                repr((new, changed, removed, delta_tree.serialize())),
            )
            return HistoryEntry(self.current_timestamp, new, changed, removed, delta_tree)
        return None


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
def _load_structured_data_tree(
    tree_type: Literal["inventory", "status_data"], hostname: Optional[HostName]
) -> Optional[StructuredDataNode]:
    """Load data of a host, cache it in the current HTTP request"""
    if not hostname:
        return None

    if "/" in hostname:
        # just for security reasons
        return None

    tree_store = StructuredDataStore(
        Path(cmk.utils.paths.inventory_output_dir)
        if tree_type == "inventory"
        else Path(cmk.utils.paths.status_data_dir)
    )

    try:
        return tree_store.load(host_name=hostname)
    except Exception as e:
        if active_config.debug:
            html.show_warning("%s" % e)
        raise LoadStructuredDataError()


def _load_status_data_tree(hostname: Optional[HostName], row: Row) -> Optional[StructuredDataNode]:
    # If no data from livestatus could be fetched (CRE) try to load from cache
    # or status dir
    raw_status_data_tree = row.get("host_structured_status")
    if not raw_status_data_tree:
        return _load_structured_data_tree("status_data", hostname)
    return StructuredDataNode.deserialize(ast.literal_eval(raw_status_data_tree.decode("utf-8")))


def _merge_inventory_and_status_data_tree(
    inventory_tree: Optional[StructuredDataNode],
    status_data_tree: Optional[StructuredDataNode],
) -> Optional[StructuredDataNode]:
    if inventory_tree is None:
        return status_data_tree

    if status_data_tree is None:
        return inventory_tree

    return inventory_tree.merge_with(status_data_tree)


def _filter_tree(struct_tree: Optional[StructuredDataNode]) -> Optional[StructuredDataNode]:
    if struct_tree is None:
        return None

    if permitted_paths := _get_permitted_inventory_paths():
        return struct_tree.get_filtered_node(
            [make_filter(entry) for entry in permitted_paths if entry]
        )

    return struct_tree


@request_memoize()
def _get_permitted_inventory_paths():
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


def has_inventory(hostname):
    if not hostname:
        return False
    inventory_path = "%s/%s" % (cmk.utils.paths.inventory_output_dir, hostname)
    return os.path.exists(inventory_path)


def inventory_of_host(host_name: HostName, api_request):
    raw_site = api_request.get("site")
    site = livestatus.SiteId(raw_site) if raw_site is not None else None
    verify_permission(host_name, site)

    row = get_status_data_via_livestatus(site, host_name)
    merged_tree = load_filtered_and_merged_tree(row)
    if not merged_tree:
        return {}

    if "paths" in api_request:
        merged_tree = merged_tree.get_filtered_node(
            [make_filter(parse_tree_path(path)) for path in api_request["paths"]]
        )

    assert merged_tree is not None
    return merged_tree.serialize()


def verify_permission(host_name: HostName, site: Optional[livestatus.SiteId]) -> None:
    if user.may("general.see_all"):
        return

    query = "GET hosts\nFilter: host_name = %s\nStats: state >= 0%s" % (
        livestatus.lqencode(host_name),
        "\nAuthUser: %s" % livestatus.lqencode(user.id) if user.id else "",
    )

    if site:
        sites.live().set_only_sites([site])

    try:
        result = sites.live().query_summed_stats(query, "ColumnHeaders: off\n")
    except livestatus.MKLivestatusNotFoundError:
        raise MKAuthException(
            _("No such inventory tree of host %s." " You may also have no access to this host.")
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
