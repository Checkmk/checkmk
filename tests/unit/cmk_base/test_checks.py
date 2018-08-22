import pytest

import cmk_base.checks as checks
import cmk_base.discovery as discovery
import cmk_base.config as config
import cmk_base.rulesets as rulesets

def test_load_checks():
    checks._initialize_data_structures()
    assert checks.check_info == {}
    checks.load()
    assert len(checks.check_info) > 1000


def test_is_tcp_check():
    checks.load()
    assert checks.is_tcp_check("xxx") == False
    assert checks.is_tcp_check("uptime") == True
    assert checks.is_tcp_check("uptime") == True
    assert checks.is_tcp_check("snmp_uptime") == False
    assert checks.is_tcp_check("mem") == True
    assert checks.is_tcp_check("mem.linux") == True
    assert checks.is_tcp_check("mem.ding") == True
    assert checks.is_tcp_check("apc_humidity") == False


def test_is_snmp_check():
    checks.load()
    assert checks.is_snmp_check("xxx") == False
    assert checks.is_snmp_check("uptime") == False
    assert checks.is_snmp_check("uptime") == False
    assert checks.is_snmp_check("snmp_uptime") == True
    assert checks.is_snmp_check("mem") == False
    assert checks.is_snmp_check("mem.linux") == False
    assert checks.is_snmp_check("mem.ding") == False
    assert checks.is_snmp_check("apc_humidity") == True
    assert checks.is_snmp_check("brocade.power") == True
    assert checks.is_snmp_check("brocade.fan") == True
    assert checks.is_snmp_check("brocade.xy") == True
    assert checks.is_snmp_check("brocade") == True


def test_discoverable_tcp_checks():
    checks.load()
    assert "uptime" in checks.discoverable_tcp_checks()
    assert "snmp_uptime" not in checks.discoverable_tcp_checks()
    assert "logwatch" in checks.discoverable_tcp_checks()


@pytest.mark.parametrize("result,ruleset", [
    (False, None),
    (False, []),
    (False, [( None, [], rulesets.ALL_HOSTS, {} )]),
    (False, [( {}, [], rulesets.ALL_HOSTS, {} )]),
    (True, [( {"status_data_inventory": True}, [], rulesets.ALL_HOSTS, {} )]),
    (False, [( {"status_data_inventory": False}, [], rulesets.ALL_HOSTS, {} )]),
])
def test_do_status_data_inventory_for(monkeypatch, result, ruleset):
    config.load_default_config()

    monkeypatch.setattr(config, "all_hosts", ["abc"])
    monkeypatch.setattr(config, "active_checks", {
        "cmk_inv": ruleset,
    })

    assert checks.do_status_data_inventory_for("abc") == result

############ Management board checks

@pytest.fixture
def _check_plugins():
    return {
        "tcp_check_mgmt_only"       : "mgmt_only",
        "tcp_check_host_precedence" : "host_precedence",
        "tcp_check_host_only"       : "host_only",
        "snmp_check_mgmt_only"      : "mgmt_only",
        "snmp_check_host_precedence": "host_precedence",
        "snmp_check_host_only"      : "host_only",
    }

############ TCP host

@pytest.mark.parametrize("for_discovery,result", [
    (False, ["tcp_check_host_precedence", "tcp_check_host_only"]),
    (True,  ["tcp_check_host_precedence", "tcp_check_host_only"]),
])
def test_filter_by_management_board_TCP_host_without_mgmt_board(monkeypatch, for_discovery, result):
    monkeypatch.setattr(config, "is_snmp_host", lambda _: False)
    monkeypatch.setattr(config, "is_tcp_host", lambda _: True)
    monkeypatch.setattr(config, "has_management_board", lambda _: False)
    monkeypatch.setattr(checks, "get_management_board_precedence", lambda c: _check_plugins()[c])
    monkeypatch.setattr(checks, "is_snmp_check", lambda c: c.startswith("snmp_"))
    found_check_plugins = [c for c in _check_plugins() if c.startswith("tcp_")]

    assert checks.filter_by_management_board("this_host", found_check_plugins,
                                             False, for_discovery=for_discovery) == set(result)

############ SNMP host

@pytest.mark.parametrize("for_discovery,result", [
    (False, ["snmp_check_host_precedence", "snmp_check_host_only"]),
    (True,  ["snmp_check_host_precedence", "snmp_check_host_only"]),
])
def test_filter_by_management_board_SNMP_host_without_mgmt_board(monkeypatch, for_discovery, result):
    monkeypatch.setattr(config, "is_snmp_host", lambda _: True)
    monkeypatch.setattr(config, "is_tcp_host", lambda _: False)
    monkeypatch.setattr(config, "has_management_board", lambda _: False)
    monkeypatch.setattr(checks, "get_management_board_precedence", lambda c: _check_plugins()[c])
    monkeypatch.setattr(checks, "is_snmp_check", lambda c: c.startswith("snmp_"))
    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]

    assert checks.filter_by_management_board("this_host", found_check_plugins,
                                             False, for_discovery=for_discovery) == set(result)

############ Dual host

@pytest.mark.parametrize("for_discovery,result", [
    (False, ["tcp_check_host_precedence",  "tcp_check_host_only",
             "snmp_check_host_precedence", "snmp_check_host_only"]),
    (True,  ["tcp_check_host_precedence",  "tcp_check_host_only",
             "snmp_check_host_precedence", "snmp_check_host_only"]),
])
def test_filter_by_management_board_dual_host_without_mgmt_board(monkeypatch, for_discovery, result):
    monkeypatch.setattr(config, "is_snmp_host", lambda _: True)
    monkeypatch.setattr(config, "is_tcp_host", lambda _: True)
    monkeypatch.setattr(config, "has_management_board", lambda _: False)
    monkeypatch.setattr(checks, "get_management_board_precedence", lambda c: _check_plugins()[c])
    monkeypatch.setattr(checks, "is_snmp_check", lambda c: c.startswith("snmp_"))
    found_check_plugins = [c for c in _check_plugins()]

    assert checks.filter_by_management_board("this_host", found_check_plugins,
                                             False, for_discovery=for_discovery) == set(result)

############ TCP host + SNMP Management Board

@pytest.mark.parametrize("for_discovery,host_result,mgmt_board_result", [
    (False,
     ["tcp_check_host_precedence", "tcp_check_host_only"],
     ["snmp_check_mgmt_only", "snmp_check_host_precedence", "snmp_check_host_only"]),
    (True,
     ["tcp_check_host_precedence", "tcp_check_host_only"],
     ["snmp_check_mgmt_only", "snmp_check_host_precedence"]),
])
def test_filter_by_management_board_TCP_host_with_SNMP_mgmt_board(monkeypatch,
                                for_discovery, host_result, mgmt_board_result):
    monkeypatch.setattr(config, "is_snmp_host", lambda _: False)
    monkeypatch.setattr(config, "is_tcp_host", lambda _: True)
    monkeypatch.setattr(config, "has_management_board", lambda _: True)
    monkeypatch.setattr(checks, "get_management_board_precedence", lambda c: _check_plugins()[c])
    monkeypatch.setattr(checks, "is_snmp_check", lambda c: c.startswith("snmp_"))
    found_check_plugins = [c for c in _check_plugins() if c.startswith("tcp_")]

    assert checks.filter_by_management_board("this_host", found_check_plugins,
                                             False, for_discovery=for_discovery) == set(host_result)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]

    assert checks.filter_by_management_board("this_host", found_check_plugins,
                                             True, for_discovery=for_discovery) == set(mgmt_board_result)

############ SNMP host + SNMP Management Board

@pytest.mark.parametrize("for_discovery,host_result,mgmt_board_result", [
    (False,
     ["snmp_check_host_only", "snmp_check_host_precedence"],
     ["snmp_check_mgmt_only"]),
    (True,
     ["snmp_check_host_only", "snmp_check_host_precedence"],
     ["snmp_check_mgmt_only"]),
])
def test_filter_by_management_board_SNMP_host_with_SNMP_mgmt_board(monkeypatch,
                                for_discovery, host_result, mgmt_board_result):
    monkeypatch.setattr(config, "is_snmp_host", lambda _: True)
    monkeypatch.setattr(config, "is_tcp_host", lambda _: False)
    monkeypatch.setattr(config, "has_management_board", lambda _: True)
    monkeypatch.setattr(checks, "get_management_board_precedence", lambda c: _check_plugins()[c])
    monkeypatch.setattr(checks, "is_snmp_check", lambda c: c.startswith("snmp_"))
    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]

    assert checks.filter_by_management_board("this_host", found_check_plugins,
                                             False, for_discovery=for_discovery) == set(host_result)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]

    assert checks.filter_by_management_board("this_host", found_check_plugins,
                                             True, for_discovery=for_discovery) == set(mgmt_board_result)

############ Dual host + SNMP Management Board

@pytest.mark.parametrize("for_discovery,host_result,mgmt_board_result", [
    (False,
     ["tcp_check_host_precedence", "tcp_check_host_only",
      "snmp_check_host_only", "snmp_check_host_precedence"],
     ["snmp_check_mgmt_only"]),
    (True,
     ["tcp_check_host_precedence", "tcp_check_host_only",
      "snmp_check_host_only", "snmp_check_host_precedence"],
     ["snmp_check_mgmt_only"]),
])
def test_filter_by_management_board_dual_host_with_SNMP_mgmt_board(monkeypatch,
                                for_discovery, host_result, mgmt_board_result):
    monkeypatch.setattr(config, "is_snmp_host", lambda _: True)
    monkeypatch.setattr(config, "is_tcp_host", lambda _: True)
    monkeypatch.setattr(config, "has_management_board", lambda _: True)
    monkeypatch.setattr(checks, "get_management_board_precedence", lambda c: _check_plugins()[c])
    monkeypatch.setattr(checks, "is_snmp_check", lambda c: c.startswith("snmp_"))
    found_check_plugins = [c for c in _check_plugins()]

    assert checks.filter_by_management_board("this_host", found_check_plugins,
                                             False, for_discovery=for_discovery) == set(host_result)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]

    assert checks.filter_by_management_board("this_host", found_check_plugins,
                                             True, for_discovery=for_discovery) == set(mgmt_board_result)
