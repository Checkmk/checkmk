#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Azure resource-type constants.

This module must stay stdlib-only (see package docstring).
"""

from collections.abc import Mapping
from typing import Final

# Abbreviations follow https://github.com/MicrosoftDocs/cloud-adoption-framework/blob/main/docs/ready/azure-best-practices/resource-abbreviations.md where possible.
# They are part of the computed unique host names ("long" mode), so changing
# an entry changes existing host names.
RESOURCE_TYPE_ABBREVIATIONS: Final[Mapping[str, str]] = {
    "Microsoft.Compute/virtualMachines": "vm",
    "Microsoft.RecoveryServices/vaults": "rsv",
    "Microsoft.Network/applicationGateways": "agw",
    "Microsoft.Network/loadBalancers": "lb",
    "Microsoft.Network/virtualNetworkGateways": "vgw",
    "Microsoft.Cache/Redis": "redis",
    "Microsoft.DocumentDB/databaseAccounts": "cosmos",
    # made-up resource type for cosmosdb databases:
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

_ABBREVIATIONS_BY_LOWERCASE_TYPE: Final[Mapping[str, str]] = {
    resource_type.lower(): abbreviation
    for resource_type, abbreviation in RESOURCE_TYPE_ABBREVIATIONS.items()
}


def get_resource_type_abbreviation(resource_type: str) -> str | None:
    # lower, because we've seen
    # e.g. "Microsoft.DocumentDB/databaseAccounts" and "Microsoft.DocumentDb/databaseAccounts"
    return _ABBREVIATIONS_BY_LOWERCASE_TYPE.get(resource_type.lower())
