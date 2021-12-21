#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# README: HISTORICAL HINT
# This inventory plugin used to be split-up into the inventory plugins "livestatus_status",
# "omd_status" and "omd_info". As the new CheckAPI enables subscribing onto multiple
# sections, this split-up is not necessary anymore and therefore the plugins were merged.

from typing import Any, Dict, Mapping, Optional, Sequence

import cmk.utils.version as cmk_version  # pylint: disable=cmk-module-layer-violation

from .agent_based_api.v1 import Attributes, register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult


def _service_status(status: Mapping[str, Sequence[str]], service_name: str):
    """
    >>> status={'stopped':['cmd', 'dcd'], 'existing':['crontab','cmd']}
    >>> _service_status(status, 'cmd')
    'stopped'
    >>> _service_status(status, 'crontab')
    'running'
    >>> _service_status(status, 'alsa-utils')
    'not existent'
    >>> _service_status({}, 'foo')
    'unknown'
    """
    if not status:
        return "unknown"
    if service_name not in status["existing"]:
        return "not existent"
    if service_name in status["stopped"]:
        return "stopped"
    return "running"


def merge_sections(
    section_livestatus_status: Mapping[str, Mapping[str, str]],
    section_omd_status: Mapping[str, Mapping],
    section_omd_info: Mapping[str, Mapping[str, Mapping]],
) -> Dict[str, Dict]:

    merged_section: Dict[str, Dict] = {"check_mk": {}, "sites": {}, "versions": {}}

    # SECTION: livestatus_status
    for site, status in section_livestatus_status.items():
        if status is None:
            continue

        # Quick workaround for enabled checker/fetcher mode. Will soon be replaced once the
        # livestatus status table has been updated.
        helper_usage_cmk = float(status["helper_usage_cmk"] or "0") * 100
        try:
            helper_usage_fetcher = float(status["helper_usage_fetcher"] or "0") * 100
            helper_usage_checker = float(status["helper_usage_checker"] or "0") * 100
        except KeyError:
            # May happen if we are trying to query old host.
            # To be consistent we correctly report that usage of the new helpers is zero.
            helper_usage_fetcher = 0.0
            helper_usage_checker = 0.0

        helper_usage_generic = float(status["helper_usage_generic"]) * 100
        livestatus_usage = float(status["livestatus_usage"]) * 100

        merged_section["sites"].setdefault(site, {"status_columns": {}, "inventory_columns": {}})[
            "status_columns"
        ] = {
            "num_hosts": status["num_hosts"],
            "num_services": status["num_services"],
            "check_helper_usage": helper_usage_generic,
            "check_mk_helper_usage": helper_usage_cmk,
            "fetcher_helper_usage": helper_usage_fetcher,
            "checker_helper_usage": helper_usage_checker,
            "livestatus_usage": livestatus_usage,
        }

    # SECTION: omd_status
    if cmk_version.is_raw_edition():
        services = [
            "nagios",
            "npcd",
        ]
    else:
        services = [
            "cmc",
            "dcd",
            "liveproxyd",
            "mknotifyd",
        ]

    services += [
        "apache",
        "crontab",
        "mkeventd",
        "rrdcached",
        "stunnel",
        "xinetd",
    ]

    num_sites = 0
    for site, omd_status in section_omd_status.items():
        # Number of sites was previously calculated from omd_info, but calculating this from
        # omd_status is way better as this section is always available
        num_sites += 1
        omd_status_dict = {}
        # create a column for each service
        for service in services:
            omd_status_dict[service] = _service_status(omd_status, service)
        merged_section["sites"].setdefault(site, {"status_columns": {}, "inventory_columns": {}})[
            "status_columns"
        ].update(omd_status_dict)

    merged_section["check_mk"]["num_sites"] = num_sites

    pre_versions = section_omd_info.get("versions", {})
    pre_sites = section_omd_info.get("sites", {})
    if not (pre_versions or pre_sites):
        return merged_section

    versions = {
        name: {
            "num_sites": 0,
            **{k: v for k, v in version.items() if k != "version"},
            "demo": (version["demo"] == "1"),
        }
        for name, version in pre_versions.items()
    }

    sites = {
        name: {
            **site_dict,
            "autostart": (site_dict["autostart"] == "1"),
        }
        for name, site_dict in pre_sites.items()
    }

    for site_dict in sites.values():
        version_dict = versions.get(site_dict["used_version"])
        if version_dict:
            version_dict["num_sites"] += 1

    merged_section["versions"] = versions
    for site, values in sites.items():
        values.pop("site", None)
        merged_section["sites"].setdefault(site, {"inventory_columns": {}, "status_columns": {}})[
            "inventory_columns"
        ].update(values)

    merged_section["check_mk"]["num_versions"] = len(versions)

    return merged_section


def generate_inventory(merged_sections: Dict[str, Any]) -> InventoryResult:

    for key, elem in merged_sections["sites"].items():
        yield TableRow(
            path=["software", "applications", "check_mk", "sites"],
            key_columns={"site": key},
            status_columns=elem["status_columns"],
            inventory_columns=elem["inventory_columns"],
        )

    for key, elem in merged_sections["versions"].items():
        yield TableRow(
            path=["software", "applications", "check_mk", "versions"],
            key_columns={"version": key},
            inventory_columns=elem,
        )

    yield Attributes(
        path=["software", "applications", "check_mk"],
        inventory_attributes={
            "num_versions": merged_sections["check_mk"].get("num_versions"),
            "num_sites": merged_sections["check_mk"].get("num_sites"),
        },
    )


def inventory_checkmk(
    section_livestatus_status: Optional[Dict[str, Dict[str, str]]],
    section_omd_status: Optional[Dict[str, Dict]],
    section_omd_info: Optional[Dict[str, Dict[str, Dict]]],
) -> InventoryResult:

    merged_sections = merge_sections(
        section_livestatus_status or {},
        section_omd_status or {},
        section_omd_info or {},
    )
    yield from generate_inventory(merged_sections)


register.inventory_plugin(
    name="inventory_checkmk",
    inventory_function=inventory_checkmk,
    sections=["livestatus_status", "omd_status", "omd_info"],
)
