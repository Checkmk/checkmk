#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

from cmk.ccc.version import Edition

from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

import cmk.plugins.azure.rulesets.azure as azure_ruleset

AZURE_VS_RULESET_VALUE: Final = {
    "authority": "global",
    "tenant": "my_tenant",
    "client": "my_client",
    "secret": ("password", "my_secret"),
    "proxy": ("url", "http://test.proxy"),
    "services": [
        "ad_connect",
        "usage_details",
        "Microsoft.Compute/virtualMachines",
        "Microsoft.Sql/servers/databases",
        "Microsoft.Storage/storageAccounts",
        "Microsoft.Web/sites",
        "Microsoft.DBforMySQL/servers",
        "Microsoft.DBforPostgreSQL/servers",
        "Microsoft.Network/trafficmanagerprofiles",
        "Microsoft.Network/loadBalancers",
    ],
    "config": {
        "explicit": [{"group_name": "foobar", "resources": ["foo", "bar"]}],
        "tag_based": [("foobar", "exists"), ("foo", ("value", "bar"))],
    },
    "piggyback_vms": "grouphost",
    "import_tags": ("filter_tags", "my_tag"),
}

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
    "piggyback_vms": "grouphost",
    "import_tags": ("filter_tags", "my_tag"),
}


def test_vs_to_fs_update() -> None:
    valuespec = convert_to_legacy_rulespec(
        azure_ruleset.rule_spec_azure, Edition.CRE, lambda x: x
    ).valuespec

    value = valuespec.transform_value(AZURE_VS_RULESET_VALUE)
    valuespec.validate_datatype(value, "")

    assert value["authority"] == AZURE_FS_RULESET_VALUE["authority"]
    assert value["tenant"] == AZURE_FS_RULESET_VALUE["tenant"]
    assert value["client"] == AZURE_FS_RULESET_VALUE["client"]
    secret = value["secret"]
    expected_secret = tuple(AZURE_FS_RULESET_VALUE["secret"])
    assert secret[0] == expected_secret[0]
    assert secret[1] == expected_secret[1]
    assert secret[2][1] == expected_secret[2][1]
    assert value["proxy"] == AZURE_FS_RULESET_VALUE["proxy"]
    assert value["config"] == AZURE_FS_RULESET_VALUE["config"]
    assert value["piggyback_vms"] == AZURE_FS_RULESET_VALUE["piggyback_vms"]
    assert value["import_tags"] == AZURE_FS_RULESET_VALUE["import_tags"]


def test_migrate_keeps_values() -> None:
    migrated = azure_ruleset._migrate_services_to_monitor(["Microsoft.DBforMySQL/flexibleServers"])
    double_migrated = azure_ruleset._migrate_services_to_monitor(migrated)
    assert migrated == ["Microsoft_DBforMySQL_slash_flexibleServers"]
    assert double_migrated == ["Microsoft_DBforMySQL_slash_flexibleServers"]


def test_migrate_silently_drops_invalid_values() -> None:
    migrated = azure_ruleset._migrate_services_to_monitor(["dadada"])
    assert len(migrated) == 0
