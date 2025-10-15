#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

import cmk.plugins.azure_v2.rulesets.azure as azure_ruleset

AZURE_FS_RULESET_VALUE: Final = {
    "authority": "global_",
    "tenant": "my_tenant",
    "client": "my_client",
    "secret": (
        "cmk_postprocessed",
        "explicit_password",
        ("uuid3933e631-dfa3-4594-925b-26179570eff3", "my_secret"),
    ),
    "proxy": ("cmk_postprocessed", "explicit_proxy", "http://test.proxy"),
    "services": [
        "ad_connect",
        "usage_details",
        "Microsoft_Compute_slash_virtualMachines",
        "Microsoft_Sql_slash_servers_slash_databases",
        "Microsoft_Storage_slash_storageAccounts",
        "Microsoft_Web_slash_sites",
        "Microsoft_DBforMySQL_slash_servers",
        "Microsoft_DBforPostgreSQL_slash_servers",
        "Microsoft_Network_slash_trafficmanagerprofiles",
        "Microsoft_Network_slash_loadBalancers",
    ],
    "config": {
        "explicit": [{"group_name": "foobar", "resources": ["foo", "bar"]}],
        "tag_based": [
            {"tag": "foobar", "condition": ("exists", None)},
            {"tag": "foo", "condition": ("equals", "bar")},
        ],
    },
    "import_tags": ("filter_tags", "my_tag"),
}


def test_migrate_keeps_values() -> None:
    migrated = azure_ruleset._migrate_services_to_monitor(["Microsoft.DBforMySQL/flexibleServers"])
    double_migrated = azure_ruleset._migrate_services_to_monitor(migrated)
    assert migrated == ["Microsoft_DBforMySQL_slash_flexibleServers"]
    assert double_migrated == ["Microsoft_DBforMySQL_slash_flexibleServers"]


def test_migrate_silently_drops_invalid_values() -> None:
    migrated = azure_ruleset._migrate_services_to_monitor(["dadada"])
    assert len(migrated) == 0
