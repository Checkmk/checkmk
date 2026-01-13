#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)

Section = Mapping[str, Mapping[str, str]]


MSSQL_VERSION_MAPPING = {
    "8": "2000",
    "9": "2005",
    "10": "2008",
    "10.50": "2008R2",
    "11": "2012",
    "12": "2014",
    "13": "2016",
    "14": "2017",
    "15": "2019",
    "16": "2022",
}


def parse_mssql_instance(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, str]] = {}
    for line in string_table:
        if (
            line[0].startswith("ERROR:")
            or len(line) < 2
            or line[1] not in ["config", "state", "details"]
        ):
            continue

        if line[0][:6] == "MSSQL_":
            # Remove the MSSQL_ prefix from the ID for this check
            instance_id = line[0][6:]
        else:
            instance_id = line[0]

        instance = parsed.setdefault(
            instance_id,
            {
                # it may happen that the state line is missing, add some fallback as default here
                "state": "0",
                "error_msg": "Unable to connect to database (Agent reported no state)",
            },
        )

        if line[1] == "config":
            instance.update(
                {
                    "version_info": f"{line[2]} - {line[3]}",
                    "cluster_name": line[4],
                    "config_version": line[2],
                    "config_edition": line[3],
                }
            )
        elif line[1] == "state":
            instance.update(
                {
                    "state": line[2],
                    "error_msg": "|".join(line[3:]),
                }
            )

        elif line[1] == "details":
            instance.update(
                {
                    "prod_version_info": f"{_parse_prod_version(line[2])} ({line[3]}) ({line[2]}) - {line[4]}",
                    "details_version": line[2],
                    "details_product": _parse_prod_version(line[2]),
                    "details_edition": line[3],
                    "details_edition_long": line[4],
                }
            )

    return parsed


def _parse_prod_version(entry: str) -> str:
    major_version, minor_version = entry.split(".", 2)[:2]
    if not (
        version := MSSQL_VERSION_MAPPING.get(
            f"{major_version}.{minor_version}",
            MSSQL_VERSION_MAPPING.get(major_version),
        )
    ):
        return f"unknown[{entry}]"
    return f"Microsoft SQL Server {version}"


agent_section_mssql_instance = AgentSection(
    name="mssql_instance",
    parse_function=parse_mssql_instance,
)


def inventorize_mssql_instance(section: Section) -> InventoryResult:
    for instance_id, attrs in section.items():
        cluster_name = attrs.get("cluster_name")
        yield TableRow(
            path=["software", "applications", "mssql", "instances"],
            key_columns={
                "name": instance_id,
            },
            inventory_columns={
                "version": _get_info("config_version", "details_version", attrs),
                "edition": _get_info("config_edition", "details_edition", attrs),
                "product": attrs.get("details_product"),
                "clustered": bool(cluster_name),
                "cluster_name": cluster_name,
            },
            status_columns={},
        )


def _get_info(key: str, alt_key: str, attrs: Mapping[str, str]) -> str | None:
    return attrs.get(key, attrs.get(alt_key))


inventory_plugin_mssql_instance = InventoryPlugin(
    name="mssql_instance",
    inventory_function=inventorize_mssql_instance,
)

# <<<mssql_instance:sep(124)>>>
# MSSQL_MSSQLSERVER|config|10.50.1600.1|Enterprise Edition|BLABLA
# <<<mssql_instance:sep(124)>>>
# MSSQL_SQLEXPRESS|config|10.50.1600.1|Express Edition|
# <<<mssql_instance:sep(124)>>>
# MSSQL_MICROSOFT##SSEE|config|9.00.5000.00|Windows Internal Database|
# <<<mssql_instance:sep(124)>>>
# MSSQL_MSSQLSERVER|state|0|[DBNETLIB][ConnectionOpen (Connect()).]SQL Server existiert nicht oder Zugriff verweigert.
# <<<mssql_instance:sep(124)>>>
# MSSQL_SQLEXPRESS|state|1|[DBNETLIB][ConnectionOpen (Connect()).]SQL Server existiert nicht oder Zugriff verweigert.
# <<<mssql_instance:sep(124)>>>
# MSSQL_MICROSOFT##SSEE|state|0|[DBNETLIB][ConnectionOpen (Connect()).]SQL Server existiert nicht oder Zugriff verweigert.

# <<<mssql_instance:sep(124)>>>
# ERROR: Failed to gather SQL server instances


def discover_mssql_instance(section: Any) -> DiscoveryResult:
    for instance_id in section:
        yield Service(item=instance_id)


def check_mssql_instance(item: str, params: Mapping[str, Any], section: Any) -> CheckResult:
    instance = section.get(item)
    if not instance:
        yield Result(
            state=State.CRIT, summary="Database or necessary processes not running or login failed"
        )
        return

    state = State.CRIT
    if params.get("map_connection_state") is not None:
        state = State(params["map_connection_state"])

    if instance["state"] == "0":
        yield Result(
            state=state, summary="Failed to connect to database (%s)" % instance["error_msg"]
        )

    yield Result(
        state=State.OK,
        summary="Version: %s" % instance.get("prod_version_info", instance["version_info"]),
    )
    if instance["cluster_name"] != "":
        yield Result(state=State.OK, summary="Clustered as %s" % instance["cluster_name"])


check_plugin_mssql_instance = CheckPlugin(
    name="mssql_instance",
    service_name="MSSQL %s Instance",
    discovery_function=discover_mssql_instance,
    check_function=check_mssql_instance,
    check_ruleset_name="mssql_instance",
    check_default_parameters={
        "map_connection_state": 2,
    },
)
