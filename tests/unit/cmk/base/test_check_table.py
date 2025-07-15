#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Mapping, Sequence

import pytest

# No stub file
from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.ccc.hostaddress import HostName

from cmk.utils.servicename import ServiceName
from cmk.utils.tags import TagGroupID, TagID

from cmk.checkengine.checking import ABCCheckingConfig, ServiceConfigurer
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.plugin_backend import get_check_plugin
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    AutocheckEntry,
    CheckPluginName,
    ConfiguredService,
    ServiceID,
)

from cmk.base.config import FilterMode, HostCheckTable


@dataclasses.dataclass(frozen=True)
class CheckingConfigTest(ABCCheckingConfig):
    rules: Mapping[HostName, Sequence[Mapping[str, object]]]

    def __call__(
        self, host_name: HostName, item: object, service_labels: object, ruleset_name: object
    ) -> Sequence[Mapping[str, object]]:
        return self.rules.get(host_name, [])


def test_cluster_ignores_nodes_parameters(
    monkeypatch: pytest.MonkeyPatch, agent_based_plugins: AgentBasedPlugins
) -> None:
    node = HostName("node")
    cluster = HostName("cluster")

    service_id = ServiceID(CheckPluginName("smart_temp"), "auto-clustered")

    ts = Scenario()
    ts.add_host(node)
    ts.add_cluster(cluster, nodes=[node])
    ts.set_ruleset(
        "clustered_services",
        [
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "Temperature SMART auto-clustered$"}],
                    "host_name": [node],
                },
                "value": True,
            }
        ],
    )
    ts.set_autochecks(node, [AutocheckEntry(*service_id, {}, {})])
    config_cache = ts.apply(monkeypatch)
    service_name_config = config_cache.make_passive_service_name_config()

    def service_description_callback(
        hostname: HostName, check_plugin_name: CheckPluginName, item: str | None
    ) -> ServiceName:
        return service_name_config.make_name(
            config_cache.label_manager.labels_of_host,
            hostname,
            check_plugin_name,
            service_name_template=(
                None
                if (p := get_check_plugin(check_plugin_name, agent_based_plugins.check_plugins))
                is None
                else p.service_name
            ),
            item=item,
        )

    # a rule for the node:
    service_configurer = ServiceConfigurer(
        CheckingConfigTest({node: [{"levels_for_node": (1, 2)}]}),
        plugins=agent_based_plugins.check_plugins,
        get_service_description=service_description_callback,
        get_effective_host=config_cache.effective_host,
        get_service_labels=config_cache.label_manager.labels_of_service,
    )

    clustered_service = config_cache.check_table(
        cluster,
        agent_based_plugins.check_plugins,
        service_configurer=service_configurer,
        service_name_config=service_name_config,
    )[service_id]
    assert clustered_service.parameters.entries == (
        TimespecificParameterSet({}, ()),
        TimespecificParameterSet({"levels": (35, 40)}, ()),
    )


def test_check_table_enforced_vs_discovered_precedence(
    monkeypatch: pytest.MonkeyPatch, agent_based_plugins: AgentBasedPlugins
) -> None:
    smart = CheckPluginName("smart_temp")
    node = HostName("node")
    cluster = HostName("cluster")

    ts = Scenario()
    ts.add_host(node)
    ts.add_cluster(cluster, nodes=[node])
    ts.set_autochecks(
        node,
        [
            AutocheckEntry(smart, "cluster-item", {"source": "autochecks"}, {}),
            AutocheckEntry(smart, "cluster-item-overridden", {"source": "autochecks"}, {}),
            AutocheckEntry(smart, "node-item", {"source": "autochecks"}, {}),
        ],
    )
    ts.set_option(
        "static_checks",
        {
            "temperature": [
                {
                    "id": "01",
                    "value": ("smart_temp", "cluster-item", {"source": "enforced-on-node"}),
                    "condition": {"host_name": [node]},
                },
                {
                    "id": "02",
                    "value": ("smart_temp", "node-item", {"source": "enforced-on-node"}),
                    "condition": {"host_name": [node]},
                },
                {
                    "id": "03",
                    "value": (
                        "smart_temp",
                        "cluster-item-overridden",
                        {"source": "enforced-on-cluster"},
                    ),
                    "condition": {"host_name": [cluster]},
                },
            ]
        },
    )
    ts.set_ruleset(
        "clustered_services",
        [
            {
                "id": "04",
                "condition": {
                    "service_description": [{"$regex": "Temperature SMART cluster"}],
                    "host_name": [node],
                },
                "value": True,
            }
        ],
    )
    config_cache = ts.apply(monkeypatch)
    service_name_config = config_cache.make_passive_service_name_config()
    check_plugins = agent_based_plugins.check_plugins
    service_configurer = config_cache.make_service_configurer(check_plugins, service_name_config)

    node_services = config_cache.check_table(
        node, check_plugins, service_configurer, service_name_config
    )
    cluster_services = config_cache.check_table(
        cluster, check_plugins, service_configurer, service_name_config
    )

    assert len(node_services) == 1
    assert len(cluster_services) == 2

    def _source_of_item(table: HostCheckTable, item: str) -> str:
        timespecific_params = table[ServiceID(smart, item)].parameters
        p = timespecific_params.evaluate(lambda _: True)
        assert p is not None
        assert not isinstance(p, tuple | list | str | int)
        return str(p["source"])

    assert _source_of_item(node_services, "node-item") == "enforced-on-node"
    assert _source_of_item(cluster_services, "cluster-item") == "enforced-on-node"
    assert _source_of_item(cluster_services, "cluster-item-overridden") == "enforced-on-cluster"


# TODO: This misses a lot of cases
# - different check_table arguments
@pytest.mark.parametrize(
    "hostname_str, filter_mode, expected_result",
    [
        ("empty-host", FilterMode.NONE, {}),
        # Skip the autochecks automatically for ping hosts
        ("ping-host", FilterMode.NONE, {}),
        (
            "no-autochecks",
            FilterMode.NONE,
            {
                (CheckPluginName("smart_temp"), "/dev/sda"): ConfiguredService(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="/dev/sda",
                    description="Temperature SMART /dev/sda",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({"levels": (35, 40)}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=True,
                ),
            },
        ),
        (
            "ignore-not-existing-checks",
            FilterMode.NONE,
            {
                (CheckPluginName("bla_blub"), "ITEM"): ConfiguredService(
                    check_plugin_name=CheckPluginName("bla_blub"),
                    item="ITEM",
                    description="Unimplemented check bla_blub / ITEM",
                    parameters=TimespecificParameters(()),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=False,
                ),
                (CheckPluginName("blub_bla"), "ITEM"): ConfiguredService(
                    check_plugin_name=CheckPluginName("blub_bla"),
                    item="ITEM",
                    description="Unimplemented check blub_bla / ITEM",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=True,
                ),
            },
        ),
        (
            "ignore-disabled-rules",
            FilterMode.NONE,
            {
                (CheckPluginName("smart_temp"), "ITEM2"): ConfiguredService(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="ITEM2",
                    description="Temperature SMART ITEM2",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({"levels": (35, 40)}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=True,
                ),
            },
        ),
        (
            "node1",
            FilterMode.NONE,
            {
                (CheckPluginName("smart_temp"), "auto-not-clustered"): ConfiguredService(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="auto-not-clustered",
                    description="Temperature SMART auto-not-clustered",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({"levels": (35, 40)}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=False,
                ),
                (CheckPluginName("smart_temp"), "static-node1"): ConfiguredService(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="static-node1",
                    description="Temperature SMART static-node1",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({"levels": (35, 40)}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=True,
                ),
            },
        ),
        (
            "cluster1",
            FilterMode.NONE,
            {
                (CheckPluginName("smart_temp"), "static-cluster"): ConfiguredService(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="static-cluster",
                    description="Temperature SMART static-cluster",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({"levels": (35, 40)}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=True,
                ),
                (CheckPluginName("smart_temp"), "auto-clustered"): ConfiguredService(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="auto-clustered",
                    description="Temperature SMART auto-clustered",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({"levels": (35, 40)}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=False,
                ),
            },
        ),
        (
            "node2",
            FilterMode.INCLUDE_CLUSTERED,
            {
                (CheckPluginName("smart_temp"), "auto-clustered"): ConfiguredService(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="auto-clustered",
                    description="Temperature SMART auto-clustered",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({"levels": (35, 40)}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=False,
                )
            },
        ),
        (
            "cluster2",
            FilterMode.INCLUDE_CLUSTERED,
            {
                (CheckPluginName("smart_temp"), "auto-clustered"): ConfiguredService(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="auto-clustered",
                    description="Temperature SMART auto-clustered",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({"levels": (35, 40)}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=False,
                )
            },
        ),
        (
            "node3",
            FilterMode.INCLUDE_CLUSTERED,
            {
                (CheckPluginName("smart_temp"), "auto-clustered"): ConfiguredService(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="auto-clustered",
                    description="Temperature SMART auto-clustered",
                    parameters=TimespecificParameters(
                        (
                            TimespecificParameterSet({}, ()),
                            TimespecificParameterSet({"levels": (35, 40)}, ()),
                        )
                    ),
                    discovered_parameters={},
                    labels={},
                    discovered_labels={},
                    is_enforced=False,
                )
            },
        ),
        (
            "node4",
            FilterMode.INCLUDE_CLUSTERED,
            {},
        ),
    ],
)
def test_check_table(
    monkeypatch: pytest.MonkeyPatch,
    hostname_str: str,
    filter_mode: FilterMode,
    expected_result: HostCheckTable,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    hostname = HostName(hostname_str)

    ts = Scenario()
    ts.add_host(hostname, tags={TagGroupID("criticality"): TagID("test")})
    ts.add_host(HostName("ping-host"), tags={TagGroupID("agent"): TagID("no-agent")})
    ts.add_host(HostName("node1"))
    ts.add_cluster(HostName("cluster1"), nodes=[HostName("node1")])
    ts.add_host(HostName("node2"))
    ts.add_host(HostName("node3"))
    ts.add_host(HostName("node4"))
    ts.add_cluster(
        HostName("cluster2"), nodes=[HostName("node2"), HostName("node3"), HostName("node4")]
    )
    ts.set_option(
        "static_checks",
        {
            "temperature": [
                {
                    "id": "01",
                    "condition": {"host_name": ["no-autochecks", "autocheck-overwrite"]},
                    "value": ("smart.temp", "/dev/sda", {}),
                },
                {
                    "id": "02",
                    "condition": {"host_name": ["ignore-not-existing-checks"]},
                    "value": ("blub.bla", "ITEM", {}),
                },
                {
                    "id": "03",
                    "condition": {"host_name": ["ignore-disabled-rules"]},
                    "options": {"disabled": True},
                    "value": ("smart.temp", "ITEM1", {}),
                },
                {
                    "id": "04",
                    "condition": {"host_name": ["ignore-disabled-rules"]},
                    "value": ("smart.temp", "ITEM2", {}),
                },
                {
                    "id": "05",
                    "condition": {"host_name": ["static-check-overwrite"]},
                    "value": ("smart.temp", "/dev/sda", {"rule": 1}),
                },
                {
                    "id": "06",
                    "condition": {"host_name": ["static-check-overwrite"]},
                    "value": ("smart.temp", "/dev/sda", {"rule": 2}),
                },
                {
                    "id": "07",
                    "condition": {"host_name": ["node1"]},
                    "value": ("smart.temp", "static-node1", {}),
                },
                {
                    "id": "08",
                    "condition": {"host_name": ["cluster1"]},
                    "value": ("smart.temp", "static-cluster", {}),
                },
            ]
        },
    )
    ts.set_ruleset(
        "clustered_services",
        [
            {
                "id": "09",
                "condition": {
                    "service_description": [{"$regex": "Temperature SMART auto-clustered$"}],
                    "host_name": [
                        HostName("node1"),
                        HostName("node2"),
                        HostName("node3"),
                    ],  # no node4 here!
                },
                "value": True,
            }
        ],
    )
    ts.set_autochecks(
        HostName("ping-host"),
        [
            AutocheckEntry(CheckPluginName("smart_temp"), "bla", {}, {}),
        ],
    )
    ts.set_autochecks(
        HostName("autocheck-overwrite"),
        [
            AutocheckEntry(CheckPluginName("smart_temp"), "/dev/sda", {"is_autocheck": True}, {}),
            AutocheckEntry(CheckPluginName("smart_temp"), "/dev/sdb", {"is_autocheck": True}, {}),
        ],
    )
    ts.set_autochecks(
        HostName("ignore-not-existing-checks"),
        [
            AutocheckEntry(CheckPluginName("bla_blub"), "ITEM", {}, {}),
        ],
    )
    ts.set_autochecks(
        HostName("node1"),
        [
            AutocheckEntry(CheckPluginName("smart_temp"), "auto-clustered", {}, {}),
            AutocheckEntry(CheckPluginName("smart_temp"), "auto-not-clustered", {}, {}),
        ],
    )
    ts.set_autochecks(
        HostName("node2"),
        [
            AutocheckEntry(CheckPluginName("smart_temp"), "auto-clustered", {}, {}),
        ],
    )

    config_cache = ts.apply(monkeypatch)
    service_name_config = config_cache.make_passive_service_name_config()

    assert set(
        config_cache.check_table(
            hostname,
            agent_based_plugins.check_plugins,
            config_cache.make_service_configurer(
                agent_based_plugins.check_plugins, service_name_config
            ),
            service_name_config,
            filter_mode=filter_mode,
        ),
    ) == set(expected_result)
    for key, value in config_cache.check_table(
        hostname,
        {},
        config_cache.make_service_configurer({}, service_name_config),
        service_name_config,
        filter_mode=filter_mode,
    ).items():
        assert key in expected_result
        assert expected_result[key] == value


@pytest.mark.parametrize(
    "hostname_str, expected_result",
    [
        ("mgmt-board-ipmi", [(CheckPluginName("mgmt_ipmi_sensors"), "TEMP X")]),
        ("ipmi-host", [(CheckPluginName("ipmi_sensors"), "TEMP Y")]),
    ],
)
def test_check_table_of_mgmt_boards(
    monkeypatch: pytest.MonkeyPatch, hostname_str: str, expected_result: list[ServiceID]
) -> None:
    hostname = HostName(hostname_str)

    ts = Scenario()
    ts.add_host(
        HostName("mgmt-board-ipmi"),
        tags={
            TagGroupID("piggyback"): TagID("auto-piggyback"),
            TagGroupID("networking"): TagID("lan"),
            TagGroupID("address_family"): TagID("no-ip"),
            TagGroupID("criticality"): TagID("prod"),
            TagGroupID("snmp_ds"): TagID("no-snmp"),
            TagGroupID("site"): TagID("heute"),
            TagGroupID("agent"): TagID("no-agent"),
        },
    )
    ts.add_host(
        HostName("ipmi-host"),
        tags={
            TagGroupID("piggyback"): TagID("auto-piggyback"),
            TagGroupID("networking"): TagID("lan"),
            TagGroupID("agent"): TagID("cmk-agent"),
            TagGroupID("criticality"): TagID("prod"),
            TagGroupID("snmp_ds"): TagID("no-snmp"),
            TagGroupID("site"): TagID("heute"),
            TagGroupID("address_family"): TagID("ip-v4-only"),
        },
    )
    ts.set_option("management_protocol", {"mgmt-board-ipmi": "ipmi"})

    ts.set_autochecks(
        HostName("mgmt-board-ipmi"),
        [AutocheckEntry(CheckPluginName("mgmt_ipmi_sensors"), "TEMP X", {}, {})],
    )
    ts.set_autochecks(
        HostName("ipmi-host"),
        [AutocheckEntry(CheckPluginName("ipmi_sensors"), "TEMP Y", {}, {})],
    )

    config_cache = ts.apply(monkeypatch)
    service_name_config = config_cache.make_passive_service_name_config()

    assert (
        list(
            config_cache.check_table(
                hostname,
                {},
                config_cache.make_service_configurer({}, service_name_config),
                service_name_config,
            ).keys()
        )
        == expected_result
    )


def test_check_table__static_checks_win(
    monkeypatch: pytest.MonkeyPatch, agent_based_plugins: AgentBasedPlugins
) -> None:
    hostname_str = "df_host"
    hostname = HostName(hostname_str)
    plugin_name = CheckPluginName("df")
    item = "/snap/core/9066"

    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "static_checks",
        {
            "filesystem": [
                {
                    "id": "01",
                    "condition": {"host_name": [hostname_str]},
                    "value": (plugin_name, item, {"source": "static"}),
                }
            ],
        },
    )
    ts.set_autochecks(hostname, [AutocheckEntry(plugin_name, item, {"source": "auto"}, {})])
    config_cache = ts.apply(monkeypatch)
    service_name_config = config_cache.make_passive_service_name_config()

    chk_table = config_cache.check_table(
        hostname,
        agent_based_plugins.check_plugins,
        config_cache.make_service_configurer(
            agent_based_plugins.check_plugins, service_name_config
        ),
        service_name_config,
    )

    # assert check table is populated as expected
    assert len(chk_table) == 1
    # assert static checks won
    effective_params = chk_table[ServiceID(plugin_name, item)].parameters.evaluate(lambda _: True)
    assert effective_params["source"] == "static"
