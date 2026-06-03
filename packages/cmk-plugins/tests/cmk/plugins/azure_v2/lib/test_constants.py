#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.azure_v2.lib import (
    get_resource_type_abbreviation,
    RESOURCE_TYPE_ABBREVIATIONS,
)

# Pinned values: the abbreviations are part of the computed unique host
# names, so changing them changes existing host names.
EXPECTED_ABBREVIATIONS = {
    "Microsoft.Compute/virtualMachines": "vm",
    "Microsoft.RecoveryServices/vaults": "rsv",
    "Microsoft.Network/applicationGateways": "agw",
    "Microsoft.Network/loadBalancers": "lb",
    "Microsoft.Network/virtualNetworkGateways": "vgw",
    "Microsoft.Cache/Redis": "redis",
    "Microsoft.DocumentDB/databaseAccounts": "cosmos",
    "Microsoft.DocumentDB/databaseAccounts/cosmos_database": "cosmosdb",
    "Microsoft.Network/azureFirewalls": "afw",
    "Microsoft.DBforMySQL/flexibleServers": "mysql",
    "Microsoft.DBforPostgreSQL/flexibleServers": "psql",
    "Microsoft.Network/virtualNetworks": "vnet",
    "Microsoft.Network/natGateways": "ng",
    "Microsoft.Sql/servers/databases": "sqldb",
    "Microsoft.Storage/storageAccounts": "st",
    "Microsoft.Web/sites": "app",
    "Microsoft.DBforMySQL/servers": "mysql",
    "Microsoft.DBforPostgreSQL/servers": "psql",
    "Microsoft.Network/trafficManagerProfiles": "traf",
}


def test_resource_type_abbreviations() -> None:
    assert dict(RESOURCE_TYPE_ABBREVIATIONS) == EXPECTED_ABBREVIATIONS


def test_get_resource_type_abbreviation_is_case_insensitive() -> None:
    # we've seen e.g. "Microsoft.DocumentDB/databaseAccounts"
    # and "Microsoft.DocumentDb/databaseAccounts"
    assert get_resource_type_abbreviation("Microsoft.DocumentDb/databaseAccounts") == "cosmos"
    assert get_resource_type_abbreviation("microsoft.compute/virtualmachines") == "vm"


def test_get_resource_type_abbreviation_unknown_type() -> None:
    assert get_resource_type_abbreviation("Microsoft.Unknown/whatever") is None
