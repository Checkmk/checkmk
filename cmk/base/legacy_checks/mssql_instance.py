#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def inventory_mssql_instance(parsed):
    for instance_id in parsed:
        yield instance_id, {}


def check_mssql_instance(item, params, parsed):
    instance = parsed.get(item)
    if not instance:
        yield 2, "Database or necessary processes not running or login failed"
        return

    state = 2
    if params is not None and params.get("map_connection_state") is not None:
        state = params["map_connection_state"]

    if instance["state"] == "0":
        yield state, "Failed to connect to database (%s)" % instance["error_msg"]

    yield 0, "Version: %s" % instance.get("prod_version_info", instance["version_info"])
    if instance["cluster_name"] != "":
        yield 0, "Clustered as %s" % instance["cluster_name"]


check_info["mssql_instance"] = LegacyCheckDefinition(
    name="mssql_instance",
    service_name="MSSQL %s Instance",
    discovery_function=inventory_mssql_instance,
    check_function=check_mssql_instance,
    check_ruleset_name="mssql_instance",
)
