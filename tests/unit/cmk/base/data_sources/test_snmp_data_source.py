#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest  # type: ignore[import]

from testlib.base import Scenario  # type: ignore[import]

from cmk.snmplib.type_defs import SNMPDetectSpec, SNMPRuleDependentDetectSpec, SNMPTree
from cmk.snmplib.snmp_scan import SNMPScanSection
from cmk.utils.type_defs import RuleSetName, SourceType

from cmk.base.api.agent_based import register
from cmk.base.api.agent_based.register import section_plugins
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources import Mode
from cmk.base.data_sources.agent import AgentHostSections
from cmk.base.data_sources.snmp import SNMPConfigurator
from cmk.base.exceptions import MKIPAddressLookupError


@pytest.fixture(name="mode", params=Mode)
def mode_fixture(request):
    return request.param


@pytest.fixture(name="hostname")
def hostname_fixture():
    return "hostname"


@pytest.fixture(name="ipaddress")
def ipaddress_fixture():
    return "1.2.3.4"


@pytest.fixture(name="scenario")
def scenario_fixture(hostname, monkeypatch):
    Scenario().add_host(hostname).apply(monkeypatch)


@pytest.fixture(name="configurator")
def configurator_source(scenario, hostname, ipaddress, mode):
    return SNMPConfigurator.snmp(hostname, ipaddress, mode=mode)


@pytest.fixture(name="source")
def source_fixture(scenario, configurator):
    return configurator.make_checker()


def test_snmp_ipaddress_from_mgmt_board_unresolvable(hostname, monkeypatch):
    def fake_lookup_ip_address(host_config, family=None, for_mgmt_board=True):
        raise MKIPAddressLookupError("Failed to ...")

    Scenario().add_host(hostname).apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(config, "host_attributes", {
        "hostname": {
            "management_address": "lolo"
        },
    })
    host_config = config.get_config_cache().get_host_config(hostname)
    assert ip_lookup.lookup_mgmt_board_ip_address(host_config) is None


def test_attribute_defaults(source, hostname, ipaddress, monkeypatch):
    assert source.id == "snmp"
    assert source._cpu_tracking_id == "snmp"

    configurator = source.configurator
    assert configurator.hostname == hostname
    assert configurator.ipaddress == ipaddress
    assert configurator.id == "snmp"
    assert configurator.cpu_tracking_id == "snmp"

    assert configurator.on_snmp_scan_error == "raise"

    # From the base class
    assert source.exception is None


def test_source_requires_ipaddress(hostname, mode, monkeypatch):
    Scenario().add_host(hostname).apply(monkeypatch)
    with pytest.raises(TypeError):
        SNMPConfigurator.snmp(hostname, None, mode=mode)


def test_description_with_ipaddress(source, monkeypatch):
    configurator = source.configurator
    default = "SNMP (Community: 'public', Bulk walk: no, Port: 161, Inline: no)"
    assert configurator.description == default


class TestSNMPConfigurator_SNMP:
    def test_attribute_defaults(self, mode, monkeypatch):
        hostname = "testhost"
        ipaddress = "1.2.3.4"

        Scenario().add_host(hostname).apply(monkeypatch)

        configurator = SNMPConfigurator.snmp(hostname, ipaddress, mode=mode)
        assert configurator.description == (
            "SNMP (Community: 'public', Bulk walk: no, Port: 161, Inline: no)")


class TestSNMPConfigurator_MGMT:
    def test_attribute_defaults(self, mode, monkeypatch):
        hostname = "testhost"
        ipaddress = "1.2.3.4"

        ts = Scenario()
        ts.add_host(hostname)
        ts.set_option("management_protocol", {hostname: "snmp"})
        ts.set_option(
            "host_attributes",
            {
                hostname: {
                    "management_address": ipaddress
                },
            },
        )
        ts.apply(monkeypatch)

        configurator = SNMPConfigurator.management_board(
            hostname,
            ipaddress,
            mode=mode,
        )
        assert configurator.description == (
            "Management board - SNMP "
            "(Community: 'public', Bulk walk: no, Port: 161, Inline: no)")


class TestSNMPSummaryResult:
    @pytest.fixture(params=(mode for mode in Mode if mode is not Mode.NONE))
    def mode(self, request):
        return request.param

    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture
    def scenario(self, hostname, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        ts.apply(monkeypatch)
        return ts

    @pytest.fixture
    def configurator(self, hostname, mode):
        return SNMPConfigurator(
            hostname,
            "1.2.3.4",
            mode=mode,
            source_type=SourceType.HOST,
            id_="snmp_id",
            cpu_tracking_id="snmp_cpu_id",
            title="snmp title",
        )

    @pytest.mark.usefixtures("scenario")
    def test_defaults(self, configurator):
        summarizer = configurator.make_summarizer()
        assert summarizer.summarize(AgentHostSections()) == (0, "Success", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_exception(self, configurator):
        checker = configurator.make_checker()
        checker.exception = Exception()
        assert checker.get_summary_result() == (3, "(?)", [])


@pytest.fixture(name="discovery_rulesets")
def discovery_rulesets_fixture(monkeypatch, hostname):
    def host_extra_conf(self, hn, rules):
        if hn == hostname:
            return rules
        return []

    def get_discovery_ruleset(ruleset_name):
        if str(ruleset_name) == 'discovery_ruleset':
            return [True]
        return []

    monkeypatch.setattr(
        config.ConfigCache,
        'host_extra_conf',
        host_extra_conf,
    )
    monkeypatch.setattr(
        register,
        'get_discovery_ruleset',
        get_discovery_ruleset,
    )


class TestSNMPConfigurator_make_snmp_scan_sections:
    @staticmethod
    def do_monkeypatch_and_make_configurator(monkeypatch, plugin, hostname, ipaddress):
        monkeypatch.setattr(
            register,
            'iter_all_snmp_sections',
            lambda: [plugin],
        )
        Scenario().add_host(hostname).apply(monkeypatch)
        return SNMPConfigurator.snmp(hostname, ipaddress, mode=Mode.DISCOVERY)

    def test_rule_indipendent(
        self,
        monkeypatch,
        hostname,
        ipaddress,
    ):
        plugin = section_plugins.create_snmp_section_plugin(
            name="norris",
            parse_function=lambda string_table: None,
            trees=[
                SNMPTree(
                    base='.1.2.3',
                    oids=['2.3'],
                ),
            ],
            detect_spec=SNMPDetectSpec([[('.1.2.3.4.5', 'Foo.*', True)]]),
        )
        snmp_configurator = self.do_monkeypatch_and_make_configurator(
            monkeypatch,
            plugin,
            hostname,
            ipaddress,
        )
        assert snmp_configurator._make_snmp_scan_sections() == [
            SNMPScanSection(
                plugin.name,
                plugin.detect_spec,
            )
        ]

    def test_rule_dependent(
        self,
        monkeypatch,
        discovery_rulesets,
        hostname,
        ipaddress,
    ):
        detect_spec_1 = SNMPDetectSpec([[('.1.2.3.4.5', 'Bar.*', False)]])
        detect_spec_2 = SNMPDetectSpec([[('.7.8.9', 'huh.*', True)]])

        def evaluator(discovery_ruleset):
            if len(discovery_ruleset) > 0 and discovery_ruleset[0]:
                return detect_spec_1
            return detect_spec_2

        plugin = section_plugins.create_snmp_section_plugin(
            name="norris",
            parse_function=lambda string_table: None,
            trees=[
                SNMPTree(
                    base='.1.2.3',
                    oids=['2.3'],
                ),
            ],
            detect_spec=SNMPDetectSpec([[('.1.2.3.4.5', 'Foo.*', True)]]),
            rule_dependent_detect_spec=SNMPRuleDependentDetectSpec(
                [RuleSetName('discovery_ruleset')],
                evaluator,
            ),
        )
        snmp_configurator = self.do_monkeypatch_and_make_configurator(
            monkeypatch,
            plugin,
            hostname,
            ipaddress,
        )
        assert snmp_configurator._make_snmp_scan_sections() == [
            SNMPScanSection(
                plugin.name,
                detect_spec_1,
            )
        ]
