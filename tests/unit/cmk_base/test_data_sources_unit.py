# pylint: disable=redefined-outer-name

import os
import pytest  # type: ignore
# No stub file
from testlib.base import Scenario  # type: ignore[import]

import cmk_base
import cmk_base.caching
import cmk_base.data_sources
import cmk_base.data_sources.abstract
import cmk_base.data_sources.programs
import cmk_base.data_sources.snmp
import cmk_base.data_sources.tcp
import cmk_base.ip_lookup as ip_lookup
import cmk_base.config as config
import cmk_base.exceptions


def test_data_source_cache_default(monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    assert not source.is_agent_cache_disabled()


def test_disable_data_source_cache(monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    assert not source.is_agent_cache_disabled()
    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled()


def test_disable_data_source_cache_no_read(mocker, monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    source.set_max_cachefile_age(999)
    source.disable_data_source_cache()

    import os
    mocker.patch.object(os.path, "exists", return_value=True)

    disabled_checker = mocker.patch.object(source, "is_agent_cache_disabled")
    assert source._read_cache_file() is None
    disabled_checker.assert_called_once()


def test_disable_data_source_cache_no_write(mocker, monkeypatch):
    Scenario().add_host("hostname").apply(monkeypatch)
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    source.disable_data_source_cache()

    disabled_checker = mocker.patch.object(source, "is_agent_cache_disabled")
    assert source._write_cache_file("X") is None
    disabled_checker.assert_called_once()


@pytest.mark.parametrize("address", [
    None,
    "",
    "any-address",
    "1.2.3.4",
])
def test_management_board_address_explicit(monkeypatch, address):
    hostname = "hostname"
    Scenario().add_host(hostname).apply(monkeypatch)
    monkeypatch.setattr(config, "host_attributes", {
        hostname: {
            "management_address": address
        },
    })

    if address:
        assert ip_lookup.lookup_mgmt_board_ip_address(hostname) == address

    else:

        def fake_lookup_ip_address(hostname, family=None, for_mgmt_board=True):
            raise cmk_base.exceptions.MKIPAddressLookupError("Failed to...")

        monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
        assert ip_lookup.lookup_mgmt_board_ip_address(hostname) is None


@pytest.mark.parametrize("tags, result", [
    ({
        "address_family": "ip-v4-only"
    }, "127.0.0.1"),
    ({
        "address_family": "ip-v4v6"
    }, "127.0.0.1"),
])
def test_management_board_address_ipv4_resolvable(monkeypatch, tags, result):
    hostname = "localhost"
    Scenario().add_host(hostname, tags=tags).apply(monkeypatch)
    assert ip_lookup.lookup_mgmt_board_ip_address(hostname) == result


@pytest.mark.skipif(
    os.environ.get('TRAVIS') == 'true',
    reason="Travis may not resolve localhost -> IPv6 (https://github.com/njh/travis-ipv6-test)")
@pytest.mark.parametrize("tags, result", [
    ({
        "address_family": "ip-v6-only"
    }, "::1"),
])
def test_management_board_address_ipv6_resolvable(monkeypatch, tags, result):
    hostname = "localhost"
    Scenario().add_host(hostname, tags=tags).apply(monkeypatch)
    assert ip_lookup.lookup_mgmt_board_ip_address(hostname) == result


@pytest.mark.parametrize("ip_in,ips_out", [
    ("1.2.{3,4,5}.6", ["1.2.3.6", "1.2.4.6", "1.2.5.6"]),
    (["0.0.0.0", "1.1.1.1/32"], ["0.0.0.0", "1.1.1.1/32"]),
    ("0.0.0.0 1.1.1.1/32", ["0.0.0.0", "1.1.1.1/32"]),
])
def test_normalize_ip(ip_in, ips_out):
    assert cmk_base.data_sources.abstract._normalize_ip_addresses(ip_in) == ips_out


@pytest.mark.parametrize("result,reported,rule", [
    (None, "127.0.0.1", None),
    (None, None, "127.0.0.1"),
    ((0, 'Allowed IP ranges: 1.2.3.4'), "1.2.3.4", "1.2.3.4"),
    ((1, 'Unexpected allowed IP ranges (exceeding: 1.2.4.6 1.2.5.6)(!)'), "1.2.{3,4,5}.6",
     "1.2.3.6"),
    ((1, 'Unexpected allowed IP ranges (missing: 1.2.3.4 1.2.3.5)(!)'), "1.2.3.6", "1.2.3.{4,5,6}"),
])
def test_tcpdatasource_only_from(monkeypatch, result, reported, rule):
    ts = Scenario().add_host("hostname")
    ts.set_option("agent_config", {"only_from": [rule]} if rule else {})
    config_cache = ts.apply(monkeypatch)

    source = cmk_base.data_sources.tcp.TCPDataSource("hostname", "ipaddress")
    monkeypatch.setattr(config_cache, "host_extra_conf", lambda host, ruleset: ruleset)
    assert source._sub_result_only_from({"onlyfrom": reported}) == result


@pytest.mark.parametrize("info_func_result,expected", [
    (
        "arg0 arg1",
        ("arg0 arg1", None),
    ),
    (
        ["arg0", "arg1"],
        ("'arg0' 'arg1'", None),
    ),
    (
        cmk_base.data_sources.programs.SpecialAgentConfiguration("arg0", None),
        ("arg0", None),
    ),
    (
        cmk_base.data_sources.programs.SpecialAgentConfiguration("arg0 arg1", None),
        ("arg0 arg1", None),
    ),
    (
        cmk_base.data_sources.programs.SpecialAgentConfiguration(["list0", "list1"], None),
        ("'list0' 'list1'", None),
    ),
    (
        cmk_base.data_sources.programs.SpecialAgentConfiguration("arg0 arg1", "stdin_blob"),
        ("arg0 arg1", "stdin_blob"),
    ),
    (
        cmk_base.data_sources.programs.SpecialAgentConfiguration(["list0", "list1"], "stdin_blob"),
        ("'list0' 'list1'", "stdin_blob"),
    ),
])
def test_get_command_line_and_stdin(monkeypatch, info_func_result, expected):
    Scenario().add_host("testhost").apply(monkeypatch)
    special_agent_id = "bi"
    agent_prefix = "share/check_mk/agents/special/agent_%s " % special_agent_id
    ds = cmk_base.data_sources.programs.SpecialAgentDataSource("testhost", "127.0.0.1",
                                                               special_agent_id, None)
    monkeypatch.setattr(config, "special_agent_info",
                        {special_agent_id: lambda a, b, c: info_func_result})
    command_line, command_stdin = ds._get_command_line_and_stdin()
    assert command_line == agent_prefix + expected[0]
    assert command_stdin == expected[1]


@pytest.mark.parametrize("hostname,settings", [
    ("agent-host", {
        "tags": {},
        "sources": ['TCPDataSource', 'PiggyBackDataSource'],
    }),
    ("ping-host", {
        "tags": {
            "agent": "no-agent"
        },
        "sources": ['PiggyBackDataSource'],
    }),
    ("snmp-host", {
        "tags": {
            "agent": "no-agent",
            "snmp_ds": "snmp-v2"
        },
        "sources": ['SNMPDataSource', 'PiggyBackDataSource'],
    }),
    ("snmpv1-host", {
        "tags": {
            "agent": "no-agent",
            "snmp_ds": "snmp-v1"
        },
        "sources": ['SNMPDataSource', 'PiggyBackDataSource'],
    }),
    ("dual-host", {
        "tags": {
            "agent": "cmk-agent",
            "snmp_ds": "snmp-v2"
        },
        "sources": ['TCPDataSource', 'SNMPDataSource', 'PiggyBackDataSource'],
    }),
    ("all-agents-host", {
        "tags": {
            "agent": "all-agents"
        },
        "sources": ['DSProgramDataSource', 'SpecialAgentDataSource', 'PiggyBackDataSource'],
    }),
    ("all-special-host", {
        "tags": {
            "agent": "special-agents"
        },
        "sources": ['SpecialAgentDataSource', 'PiggyBackDataSource'],
    }),
])
def test_data_sources_of_hosts(monkeypatch, hostname, settings):
    ts = Scenario().add_host(hostname, tags=settings["tags"])
    ts.set_ruleset("datasource_programs", [
        ('echo 1', [], ['ds-host-14', 'all-agents-host', 'all-special-host'], {}),
    ])
    ts.set_option(
        "special_agents",
        {"jolokia": [({}, [], [
            'special-host-14',
            'all-agents-host',
            'all-special-host',
        ], {}),]})
    ts.apply(monkeypatch)

    sources = cmk_base.data_sources.DataSources(hostname, "127.0.0.1")
    source_names = [s.__class__.__name__ for s in sources.get_data_sources()]
    assert settings["sources"] == source_names, "Wrong sources for %s" % hostname
