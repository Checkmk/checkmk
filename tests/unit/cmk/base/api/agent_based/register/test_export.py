#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections import defaultdict
from typing import Iterator, Mapping
from unittest.mock import patch

import pytest

from cmk.utils.type_defs import CheckPluginName, InventoryPluginName, RuleSetName, SectionName

from cmk.base.api.agent_based.checking_classes import DiscoveryResult
from cmk.base.api.agent_based.inventory_classes import InventoryResult
from cmk.base.api.agent_based.register import (
    _config,
    export,
    is_registered_agent_section_plugin,
    is_registered_check_plugin,
    is_registered_inventory_plugin,
    is_registered_snmp_section_plugin,
    is_stored_ruleset,
)
from cmk.base.api.agent_based.section_classes import SNMPTree
from cmk.base.api.agent_based.type_defs import HostLabelGenerator, Parameters
from cmk.base.api.agent_based.utils import startswith

from .test_check_plugins import dummy_function_ips
from .test_section_plugins import parse_dummy


def dummy_host_label_function(
    params: Parameters,
    section: Mapping,
) -> HostLabelGenerator:
    yield from ()


def dummy_discovery_function(
    params: Parameters,
    section: Mapping,
) -> DiscoveryResult:
    return
    yield


def dummy_inventory_function(
    params: Parameters,
    section: Mapping,
) -> InventoryResult:
    return
    yield


@pytest.fixture(name="valid_plugin_module_name")
def fixture_valid_plugin_module_name() -> Iterator[None]:
    with patch.object(export, "get_validated_plugin_module_name") as mocked_method:
        mocked_method.side_effect = lambda: None
        yield


@pytest.fixture(name="empty_registry")
def fixture_empty_registry(monkeypatch) -> Iterator[None]:
    monkeypatch.setattr(_config, "registered_agent_sections", {})
    monkeypatch.setattr(_config, "registered_snmp_sections", {})
    monkeypatch.setattr(_config, "registered_check_plugins", {})
    monkeypatch.setattr(_config, "registered_inventory_plugins", {})
    monkeypatch.setattr(_config, "stored_rulesets", {})
    monkeypatch.setattr(_config, "_sections_by_parsed_name", defaultdict(dict))
    monkeypatch.setattr(_config, "_check_plugins_by_ruleset_name", defaultdict(list))
    yield


def test_agent_section_side_effects(valid_plugin_module_name, empty_registry):

    section = SectionName("agent_section")
    ruleset = RuleSetName("a_great_agent_section_host_label_rule")

    assert not is_registered_agent_section_plugin(section)
    assert not is_stored_ruleset(ruleset)

    export.agent_section(
        name="agent_section",
        parse_function=parse_dummy,
        host_label_function=dummy_host_label_function,
        host_label_default_parameters={},
        host_label_ruleset_name="a_great_agent_section_host_label_rule",
    )

    assert is_registered_agent_section_plugin(section)
    assert is_stored_ruleset(ruleset)


def test_snmp_section_side_effects(valid_plugin_module_name, empty_registry):

    section = SectionName("snmp_section")
    ruleset = RuleSetName("a_great_snmp_host_label_rule")

    assert not is_registered_snmp_section_plugin(section)
    assert not is_stored_ruleset(ruleset)

    export.snmp_section(
        name="snmp_section",
        detect=startswith(".1", "foobar"),
        fetch=SNMPTree(base=".1", oids=["1"]),
        parse_function=parse_dummy,
        host_label_function=dummy_host_label_function,
        host_label_default_parameters={},
        host_label_ruleset_name="a_great_snmp_host_label_rule",
    )

    assert is_registered_snmp_section_plugin(section)
    assert is_stored_ruleset(ruleset)


def test_check_plugin_side_effects(valid_plugin_module_name, empty_registry):

    plugin = CheckPluginName("check_plugin")
    ruleset = RuleSetName("a_discovery_rulset")

    assert not is_registered_check_plugin(plugin)
    assert not is_stored_ruleset(ruleset)

    export.check_plugin(
        name="check_plugin",
        service_name="foobar %s",
        discovery_function=dummy_discovery_function,
        discovery_ruleset_name="a_discovery_rulset",
        discovery_default_parameters={},
        check_function=dummy_function_ips,
        check_ruleset_name="a_check_ruleset",
        check_default_parameters={},
    )

    assert is_registered_check_plugin(plugin)
    assert is_stored_ruleset(ruleset)


def test_inventory_plugin_side_effects(valid_plugin_module_name, empty_registry):

    plugin = InventoryPluginName("inventory_plugin")

    assert not is_registered_inventory_plugin(plugin)

    export.inventory_plugin(
        name="inventory_plugin",
        inventory_function=dummy_inventory_function,
        inventory_ruleset_name="an_inventory_rulset",
        inventory_default_parameters={},
    )

    assert is_registered_inventory_plugin(plugin)
