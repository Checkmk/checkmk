#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping, Sequence
from datetime import timedelta
from pathlib import Path
from typing import Literal, TypedDict

import livestatus

from cmk.ccc.exceptions import MKException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId

import cmk.utils.paths
from cmk.utils.structured_data import (
    ImmutableTree,
    InventoryPaths,
    SDFilterChoice,
    SDRawTree,
    serialize_tree,
)

from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import PageRegistry
from cmk.gui.valuespec import ValueSpec
from cmk.gui.views.icon import IconRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.visuals.info import VisualInfo, VisualInfoRegistry
from cmk.gui.watolib.rulespecs import RulespecGroupRegistry, RulespecRegistry

from . import _rulespec, _xml
from ._icon import InventoryHistoryIcon, InventoryIcon
from ._rulespec import RulespecGroupInventory
from ._tree import (
    get_history,
    get_short_inventory_filepath,
    InventoryPath,
    load_delta_tree,
    load_latest_delta_tree,
    load_tree,
    make_filter_choices_from_api_request_paths,
    parse_inventory_path,
    TreeSource,
)
from ._valuespecs import vs_element_inventory_visible_raw_path, vs_inventory_path_or_keys_help
from .filters import FilterHasInv, FilterInvHasSoftwarePackage

__all__ = [
    "InventoryPath",
    "RulespecGroupInventory",
    "TreeSource",
    "get_history",
    "get_short_inventory_filepath",
    "load_delta_tree",
    "load_tree",
    "load_latest_delta_tree",
    "parse_inventory_path",
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
            callable=InventoryHousekeeping(cmk.utils.paths.omd_root),
            interval=timedelta(hours=12),
        )
    )
    visual_info_registry.register(VisualInfoInventoryHistory)
    filter_registry.register(FilterHasInv())
    filter_registry.register(FilterInvHasSoftwarePackage())
    _rulespec.register(rulespec_group_registry, rulespec_registry)
    icon_and_action_registry.register(InventoryIcon)
    icon_and_action_registry.register(InventoryHistoryIcon)


def verify_permission(site_id: SiteId | None, host_name: HostName) -> None:
    if user.may("general.see_all"):
        return

    query = "GET hosts\nFilter: host_name = {}\nStats: state >= 0{}".format(
        livestatus.lqencode(host_name),
        "\nAuthUser: %s" % livestatus.lqencode(user.id) if user.id else "",
    )

    if site_id:
        sites.live().set_only_sites([site_id])

    try:
        result = sites.live().query_summed_stats(query, "ColumnHeaders: off\n")
    except livestatus.MKLivestatusNotFoundError:
        raise MKAuthException(
            _("No such inventory tree of host %s. You may also have no access to this host.")
            % host_name
        )
    finally:
        if site_id:
            sites.live().set_only_sites()

    if result[0] == 0:
        raise MKAuthException(_("You are not allowed to access the host %s.") % host_name)


def get_raw_status_data_via_livestatus(site: SiteId | None, host_name: HostName) -> bytes:
    query = (
        "GET hosts\nColumns: host_structured_status\nFilter: host_name = %s\n"
        % livestatus.lqencode(host_name)
    )
    try:
        sites.live().set_only_sites([site] if site else None)
        result = sites.live().query(query)
    finally:
        sites.live().set_only_sites()

    if result and result[0]:
        return result[0][0]
    return b""


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
    try:
        HostAddress(hostname)
    except ValueError:
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


def _inventory_of_host(
    site_id: SiteId | None, host_name: HostName, filters: Sequence[SDFilterChoice]
) -> ImmutableTree:
    verify_permission(site_id, host_name)
    tree = load_tree(
        host_name=host_name,
        raw_status_data_tree=get_raw_status_data_via_livestatus(site_id, host_name),
    )
    return tree.filter(filters) if filters else tree


def _write_json(resp):
    response.set_data(json.dumps(resp, sort_keys=True, indent=4, separators=(",", ": ")))


def _write_xml(resp):
    dom = _xml.dict_to_document(resp)
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
        for raw_host_name in hosts:
            _check_for_valid_hostname(raw_host_name)
            result[raw_host_name] = serialize_tree(
                _inventory_of_host(
                    SiteId(raw_site_id) if (raw_site_id := api_request.get("site")) else None,
                    HostName(raw_host_name),
                    (
                        make_filter_choices_from_api_request_paths(api_request["paths"])
                        if "paths" in api_request
                        else []
                    ),
                )
            )

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
    def __init__(self, omd_root: Path) -> None:
        super().__init__()
        self.inv_paths = InventoryPaths(omd_root)

    def __call__(self) -> None:
        if not (self.inv_paths.delta_cache_dir.exists() and self.inv_paths.archive_dir.exists()):
            return

        inventory_archive_hosts = {
            x.name for x in self.inv_paths.archive_dir.iterdir() if x.is_dir()
        }
        inventory_delta_cache_hosts = {
            x.name for x in self.inv_paths.delta_cache_dir.iterdir() if x.is_dir()
        }

        folders_to_delete = inventory_delta_cache_hosts - inventory_archive_hosts
        for foldername in folders_to_delete:
            shutil.rmtree(str(self.inv_paths.delta_cache_host(HostName(foldername))))

        inventory_delta_cache_hosts -= folders_to_delete
        for raw_host_name in inventory_delta_cache_hosts:
            host_name = HostName(raw_host_name)
            available_timestamps = self._get_timestamps_for_host(host_name)
            for file_path in [
                x for x in self.inv_paths.delta_cache_host(host_name).iterdir() if not x.is_dir()
            ]:
                delete = False
                try:
                    first, second = file_path.with_suffix("").name.split("_")
                    if not (first in available_timestamps and second in available_timestamps):
                        delete = True
                except ValueError:
                    delete = True
                if delete:
                    file_path.unlink()

    def _get_timestamps_for_host(self, host_name: HostName) -> set[str]:
        timestamps = {"None"}  # 'None' refers to the histories start
        tree_path = self.inv_paths.inventory_tree(host_name)
        try:
            timestamps.add(str(int(tree_path.stat().st_mtime)))
        except FileNotFoundError:
            # TODO CMK-23408
            try:
                timestamps.add(str(int(tree_path.legacy.stat().st_mtime)))
            except FileNotFoundError:
                pass

        for filename in [
            x for x in self.inv_paths.archive_host(host_name).iterdir() if not x.is_dir()
        ]:
            timestamps.add(filename.with_suffix("").name)
        return timestamps


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
