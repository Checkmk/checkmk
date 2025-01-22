#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import storeonce
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

# If have no idea what exactly this is...
Appliance = Mapping[str, Any]

Section = Mapping[str, Appliance]

_APP_STATE_MAP = {"Reachable": State.OK}

# Currently used metrics
_PROPERTIES_FEDERATION = (
    "hostname",
    "address",
    "productName",
    "serialNumber",
    "localhost",
    "applianceState",
    "stateUpdatedDate",
    "federationApiVersion",
    "applianceStateString",
    "sinceStateUpdatedSeconds",
)

_PROPERTIES_DASHBOARD = (
    "softwareUpdateRecommended",
    "softwareVersion",
    "localFreeBytes",
    "localCapacityBytes",
    "cloudFreeBytes",
    "cloudCapacityBytes",
    "metricsCpuTotal",
    "metricsMemoryUsedPercent",
    "metricsDataDiskUtilisationPercent",
    "applianceStatusString",
    "dataServicesStatusString",
    "licenseStatus",
    "licenseStatusString",
    "userStorageStatusString",
    "hardwareStatusString",
    "catStoresSummary",
    "cloudBankStoresSummary",
    "nasSharesSummary",
    "vtlLibrariesSummary",
    "nasRepMappingSummary",
    "vtlRepMappingSummary",
    "dedupeRatio",
)


_LICENSE_MAP = {
    "OK": State.OK,
    "WARNING": State.WARN,
    "CRITICAL": State.CRIT,
    "NOT_HARDWARE": State.UNKNOWN,
    "NOT_APPLICABLE": State.UNKNOWN,
}


def parse_storeonce4x_appliances(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, Any]] = {}

    federation_json = json.loads(string_table[0][0])
    dashboard_json_list = [json.loads(json_obj[0]) for json_obj in string_table[1:]]

    for member in federation_json["members"]:
        hostname = member["hostname"]

        parsed[hostname] = {}
        for mem_property in _PROPERTIES_FEDERATION:
            parsed[hostname][mem_property] = member[mem_property]

        parsed[hostname]["cmk_state"] = _APP_STATE_MAP.get(
            member["applianceStateString"], State.UNKNOWN
        )

    # For every member uuid, we have more metrics in the dashboard
    for hostname, prop in parsed.items():
        for dashboard_elem in dashboard_json_list:
            if hostname == dashboard_elem["hostname"]:
                for dashboard_property in _PROPERTIES_DASHBOARD:
                    prop[dashboard_property] = dashboard_elem[dashboard_property]

        # Calculate missing metrics (which where previously available in REST API 3x)
        for name in ("Free", "Capacity"):
            prop["combined%sBytes" % name] = (
                prop["cloud%sBytes" % name] + prop["local%sBytes" % name]
            )

    return parsed


agent_section_storeonce4x_appliances = AgentSection(
    name="storeonce4x_appliances",
    parse_function=parse_storeonce4x_appliances,
)


def discover_storeonce4x_appliances(section: Section) -> DiscoveryResult:
    yield from (Service(item=host) for host in section)


def check_storeonce4x_appliances(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    yield Result(
        state=data["cmk_state"],
        summary="State: %s, Serial Number: %s, Software version: %s, Product Name: %s"
        % (
            data["applianceStateString"],
            data["serialNumber"],
            data["softwareVersion"],
            data["productName"],
        ),
    )


check_plugin_storeonce4x_appliances = CheckPlugin(
    name="storeonce4x_appliances",
    service_name="Appliance %s Status",
    discovery_function=discover_storeonce4x_appliances,
    check_function=check_storeonce4x_appliances,
)


def check_storeonce4x_appliances_storage(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    yield from storeonce.check_storeonce_space(item, params, data)


check_plugin_storeonce4x_appliances_storage = CheckPlugin(
    name="storeonce4x_appliances_storage",
    service_name="Appliance %s Storage",
    sections=["storeonce4x_appliances"],
    discovery_function=discover_storeonce4x_appliances,
    check_function=check_storeonce4x_appliances_storage,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)


def check_storeonce4x_appliances_license(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    yield Result(
        state=_LICENSE_MAP.get(data["licenseStatus"], State.UNKNOWN),
        summary="Status: %s" % data["licenseStatusString"],
    )


check_plugin_storeonce4x_appliances_license = CheckPlugin(
    name="storeonce4x_appliances_license",
    service_name="Appliance %s License",
    sections=["storeonce4x_appliances"],
    discovery_function=discover_storeonce4x_appliances,
    check_function=check_storeonce4x_appliances_license,
)


def check_storeonce4x_appliances_summaries(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    for summary, summary_descr in (
        ("catStoresSummary", "Cat stores"),
        ("cloudBankStoresSummary", "Cloud bank"),
        ("nasSharesSummary", "NAS Shares"),
        ("vtlLibrariesSummary", "VTL Libraries"),
        ("nasRepMappingSummary", "NAS Replication Mapping"),
        ("vtlRepMappingSummary", "VTL Replication Mapping"),
    ):
        for descr, state in (
            ("Ok", State.OK),
            ("Warning", State.WARN),
            ("Critical", State.CRIT),
            ("Unknown", State.UNKNOWN),
        ):
            numbers = data[summary]["statusSummary"]["num%s" % descr]
            total = data[summary]["statusSummary"]["total"]
            if numbers == 0:
                continue
            yield Result(
                state=state,
                summary=f"{summary_descr} {descr} ({numbers} of {total})",
            )


check_plugin_storeonce4x_appliances_summaries = CheckPlugin(
    name="storeonce4x_appliances_summaries",
    service_name="Appliance %s Summaries",
    sections=["storeonce4x_appliances"],
    discovery_function=discover_storeonce4x_appliances,
    check_function=check_storeonce4x_appliances_summaries,
)
