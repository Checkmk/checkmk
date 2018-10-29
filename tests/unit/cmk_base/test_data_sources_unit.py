import pytest

import cmk_base.data_sources.abstract
import cmk_base.data_sources.programs
import cmk_base.data_sources.snmp
import cmk_base.data_sources.tcp
import cmk_base.ip_lookup as ip_lookup
import cmk_base.config as config
import cmk_base.exceptions


def test_data_source_cache_default():
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    assert not source.is_agent_cache_disabled()


def test_disable_data_source_cache():
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    assert not source.is_agent_cache_disabled()
    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled()


def test_disable_data_source_cache_no_read(mocker):
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    source.set_max_cachefile_age(999)
    source.disable_data_source_cache()

    import os
    mocker.patch.object(os.path, "exists", return_value=True)

    disabled_checker = mocker.patch.object(source, "is_agent_cache_disabled")
    assert source._read_cache_file() is None
    disabled_checker.assert_called_once()


def test_disable_data_source_cache_no_write(mocker):
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    source.disable_data_source_cache()

    disabled_checker = mocker.patch.object(source, "is_agent_cache_disabled")
    assert source._write_cache_file("X") is None
    disabled_checker.assert_called_once()


def test_mgmt_board_data_source_is_ip_address():
    _is_ipaddress = cmk_base.data_sources.abstract.ManagementBoardDataSource._is_ipaddress
    assert _is_ipaddress(None) == False
    assert _is_ipaddress("localhost") == False
    assert _is_ipaddress("abc 123") == False
    assert _is_ipaddress("127.0.0.1") == True
    assert _is_ipaddress("::1") == True
    assert _is_ipaddress("fe80::807c:f8ff:fea9:9f12") == True


@pytest.mark.parametrize("result,address,resolvable", [
    (None, None, True),
    ("127.0.0.1", "127.0.0.1", True),
    ("127.0.1.1", "lolo", True),
    (None, "lolo", False),
])
def test_mgmt_board_data_source_management_board_ipaddress(monkeypatch, result, address,
                                                           resolvable):
    source = cmk_base.data_sources.snmp.SNMPManagementBoardDataSource("hostname", "ipaddress")

    if resolvable:
        monkeypatch.setattr(ip_lookup, "lookup_ip_address", lambda h: "127.0.1.1")
    else:

        def raise_exc(h):
            raise cmk_base.exceptions.MKIPAddressLookupError("Failed to...")

        monkeypatch.setattr(ip_lookup, "lookup_ip_address", raise_exc)

    monkeypatch.setattr(config, "management_address_of", lambda h: address)
    assert source._management_board_ipaddress("hostname") == result


@pytest.mark.parametrize("ip_in,ips_out", [
    ("1.2.{3,4,5}.6", ["1.2.3.6", "1.2.4.6", "1.2.5.6"]),
    (["0.0.0.0", "1.1.1.1/32"], ["0.0.0.0", "1.1.1.1/32"]),
    ("0.0.0.0 1.1.1.1/32", ["0.0.0.0", "1.1.1.1/32"]),
])
def test_normalize_ip(ip_in, ips_out):
    assert cmk_base.data_sources.tcp._normalize_ip_addresses(ip_in) == ips_out


@pytest.mark.parametrize("result,reported,rule", [
    ((0, ''), "127.0.0.1", None),
    ((0, ''), None, "127.0.0.1"),
    ((0, ', allowed IP ranges: 1.2.3.4'), "1.2.3.4", "1.2.3.4"),
    ((1, ', invalid access configuration:'
      ' agent allows extra: 1.2.4.6 1.2.5.6(!)'), "1.2.{3,4,5}.6", "1.2.3.6"),
    ((1, ', invalid access configuration:'
      ' agent blocks: 1.2.3.5 1.2.3.4(!)'), "1.2.3.6", "1.2.3.{4,5,6}"),
])
def test_tcpdatasource_only_from(monkeypatch, result, reported, rule):
    source = cmk_base.data_sources.tcp.TCPDataSource("hostname", "ipaddress")

    monkeypatch.setattr(config, "agent_config", {"only_from": [rule]} if rule else {})
    monkeypatch.setattr(config, "host_extra_conf", lambda host, ruleset: ruleset)

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
    special_agent_id = "bi"
    agent_prefix = "share/check_mk/agents/special/agent_%s " % special_agent_id
    ds = cmk_base.data_sources.programs.SpecialAgentDataSource("testhost", "127.0.0.1",
                                                               special_agent_id, None)
    monkeypatch.setattr(config, "special_agent_info",
                        {special_agent_id: lambda a, b, c: info_func_result})
    command_line, command_stdin = ds._get_command_line_and_stdin()
    assert command_line == agent_prefix + expected[0]
    assert command_stdin == expected[1]
