#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
import shutil
import time
import xml.dom.minidom
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, TypedDict

import dicttoxml  # type: ignore[import-untyped]

import livestatus

from cmk.ccc.exceptions import MKException

import cmk.utils.paths
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.structured_data import SDRawTree, serialize_tree

from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import PageRegistry
from cmk.gui.type_defs import Row
from cmk.gui.valuespec import ValueSpec
from cmk.gui.views.icon import IconRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.visuals.info import VisualInfo, VisualInfoRegistry
from cmk.gui.watolib.rulespecs import RulespecGroupRegistry, RulespecRegistry

from . import _rulespec
from ._history import (
    FilteredInventoryHistoryPaths,
    FilterInventoryHistoryPathsError,
    get_history,
    HistoryEntry,
    InventoryHistoryPath,
    load_delta_tree,
    load_latest_delta_tree,
)
from ._icon import InventoryIcon
from ._rulespec import RulespecGroupInventory
from ._store import has_inventory
from ._tree import (
    get_short_inventory_filepath,
    InventoryPath,
    load_filtered_and_merged_tree,
    make_filter_choices_from_api_request_paths,
    parse_inventory_path,
    TreeSource,
)
from ._valuespecs import vs_element_inventory_visible_raw_path, vs_inventory_path_or_keys_help
from .filters import FilterHasInv, FilterInvHasSoftwarePackage

__all__ = [
    "FilteredInventoryHistoryPaths",
    "FilterInventoryHistoryPathsError",
    "get_history",
    "get_short_inventory_filepath",
    "has_inventory",
    "HistoryEntry",
    "InventoryHistoryPath",
    "InventoryPath",
    "load_delta_tree",
    "load_filtered_and_merged_tree",
    "load_latest_delta_tree",
    "parse_inventory_path",
    "RulespecGroupInventory",
    "TreeSource",
    "vs_element_inventory_visible_raw_path",
    "vs_inventory_path_or_keys_help",
]


def register(
    page_registry: PageRegistry,
    visual_info_registry: VisualInfoRegistry,
    filter_registry: FilterRegistry,
    rulespec_group_registry: RulespecGroupRegistry,
    rulespec_registry: RulespecRegistry,
    icon_and_action_registry: IconRegistry,
    cron_job_registry: CronJobRegistry,
) -> None:
    page_registry.register_page_handler("host_inv_api", page_host_inv_api)
    cron_job_registry.register(
        CronJob(
            name="execute_inventory_housekeeping_job",
            callable=execute_inventory_housekeeping_job,
            interval=timedelta(hours=12),
        )
    )
    visual_info_registry.register(VisualInfoInventoryHistory)
    filter_registry.register(FilterHasInv())
    filter_registry.register(FilterInvHasSoftwarePackage())
    _rulespec.register(rulespec_group_registry, rulespec_registry)
    icon_and_action_registry.register(InventoryIcon)


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


# .
#   .--Inventory API-------------------------------------------------------.
#   |   ___                      _                        _    ____ ___    |
#   |  |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _     / \  |  _ \_ _|   |
#   |   | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |   / _ \ | |_) | |    |
#   |   | || | | \ V /  __/ | | | || (_) | |  | |_| |  / ___ \|  __/| |    |
#   |  |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, | /_/   \_\_|  |___|   |
#   |                                          |___/                       |
#   '----------------------------------------------------------------------'


def _check_for_valid_hostname(hostname: str) -> None:
    """test hostname for invalid chars, raises MKUserError if invalid chars are found
    >>> _check_for_valid_hostname("klappspaten")
    >>> _check_for_valid_hostname("../../etc/passwd")
    Traceback (most recent call last):
    cmk.gui.exceptions.MKUserError: You need to provide a valid "host name". Only letters, digits, dash, underscore and dot are allowed.
    """
    if HostAddress.is_valid(hostname):
        return
    raise MKUserError(
        None,
        _(
            'You need to provide a valid "host name". '
            "Only letters, digits, dash, underscore and dot are allowed.",
        ),
    )


class _HostInvAPIResponse(TypedDict):
    result_code: Literal[0, 1]
    result: str | Mapping[str, SDRawTree]


def _inventory_of_host(host_name: HostName, api_request: dict[str, Any]) -> SDRawTree:
    raw_site = api_request.get("site")
    site = livestatus.SiteId(raw_site) if raw_site is not None else None
    verify_permission(host_name, site)

    tree = load_filtered_and_merged_tree(get_status_data_via_livestatus(site, host_name))
    if "paths" in api_request:
        return serialize_tree(
            tree.filter(make_filter_choices_from_api_request_paths(api_request["paths"]))
        )
    return serialize_tree(tree)


def _write_json(resp):
    response.set_data(json.dumps(resp, sort_keys=True, indent=4, separators=(",", ": ")))


def _write_xml(resp):
    unformated_xml = dicttoxml.dicttoxml(resp)
    dom = xml.dom.minidom.parseString(unformated_xml)
    response.set_data(dom.toprettyxml())


def _write_python(resp):
    response.set_data(repr(resp))


def page_host_inv_api() -> None:
    resp: _HostInvAPIResponse
    try:
        api_request = request.get_request()
        if not (hosts := api_request.get("hosts")):
            if (host_name := api_request.get("host")) is None:
                raise MKUserError("host", _('You need to provide a "host".'))
            hosts = [host_name]

        result: dict[str, SDRawTree] = {}
        for a_host_name in hosts:
            _check_for_valid_hostname(a_host_name)
            result[a_host_name] = _inventory_of_host(a_host_name, api_request)

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


class VisualInfoInventoryHistory(VisualInfo):
    @property
    def ident(self) -> str:
        return "invhist"

    @property
    def title(self) -> str:
        return _("Inventory history")

    @property
    def title_plural(self) -> str:
        return _("Inventory histories")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return []
