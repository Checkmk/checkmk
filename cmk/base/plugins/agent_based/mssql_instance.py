#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Mapping, Optional

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, Mapping[str, str]]


def parse_mssql_instance(string_table: StringTable) -> Section:
    parsed: Dict[str, Dict[str, str]] = {}
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
                    "version_info": "%s - %s" % (line[2], line[3]),
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
                    "prod_version_info": "%s (%s) (%s) - %s"
                    % (_parse_prod_version(line[2]), line[3], line[2], line[4]),
                    "details_version": line[2],
                    "details_product": _parse_prod_version(line[2]),
                    "details_edition": line[3],
                    "details_edition_long": line[4],
                }
            )

    return parsed


def _parse_prod_version(entry: str) -> str:
    if entry.startswith("8."):
        version = "2000"
    elif entry.startswith("9."):
        version = "2005"
    elif entry.startswith("10.0"):
        version = "2008"
    elif entry.startswith("10.50"):
        version = "2008R2"
    elif entry.startswith("11."):
        version = "2012"
    elif entry.startswith("12."):
        version = "2014"
    elif entry.startswith("13."):
        version = "2016"
    elif entry.startswith("14."):
        version = "2017"
    elif entry.startswith("15."):
        version = "2019"
    else:
        return "unknown[%s]" % entry
    return "Microsoft SQL Server %s" % version


register.agent_section(
    name="mssql_instance",
    parse_function=parse_mssql_instance,
)


def inventory_mssql_instance(section: Section) -> InventoryResult:
    path = ["software", "applications", "mssql", "instances"]
    for instance_id, attrs in section.items():
        cluster_name = attrs.get("cluster_name")
        yield TableRow(
            path=path,
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


def _get_info(key: str, alt_key: str, attrs: Mapping[str, str]) -> Optional[str]:
    return attrs.get(key, attrs.get(alt_key))


register.inventory_plugin(
    name="mssql_instance",
    inventory_function=inventory_mssql_instance,
)
