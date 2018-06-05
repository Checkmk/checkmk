import pytest

import cmk_base.checks as checks
import cmk_base.discovery as discovery
import cmk_base.config as config
import cmk_base.rulesets as rulesets
import cmk_base.check_utils

def test_load_checks():
    checks._initialize_data_structures()
    assert checks.check_info == {}
    checks.load()
    assert len(checks.check_info) > 1000


def test_is_tcp_check():
    checks.load()
    assert cmk_base.check_utils.is_tcp_check("xxx") == False
    assert cmk_base.check_utils.is_tcp_check("uptime") == True
    assert cmk_base.check_utils.is_tcp_check("uptime") == True
    assert cmk_base.check_utils.is_tcp_check("snmp_uptime") == False
    assert cmk_base.check_utils.is_tcp_check("mem") == True
    assert cmk_base.check_utils.is_tcp_check("mem.linux") == True
    assert cmk_base.check_utils.is_tcp_check("mem.ding") == True
    assert cmk_base.check_utils.is_tcp_check("apc_humidity") == False


def test_is_snmp_check():
    checks.load()
    assert cmk_base.check_utils.is_snmp_check("xxx") == False
    assert cmk_base.check_utils.is_snmp_check("uptime") == False
    assert cmk_base.check_utils.is_snmp_check("uptime") == False
    assert cmk_base.check_utils.is_snmp_check("snmp_uptime") == True
    assert cmk_base.check_utils.is_snmp_check("mem") == False
    assert cmk_base.check_utils.is_snmp_check("mem.linux") == False
    assert cmk_base.check_utils.is_snmp_check("mem.ding") == False
    assert cmk_base.check_utils.is_snmp_check("apc_humidity") == True
    assert cmk_base.check_utils.is_snmp_check("brocade.power") == True
    assert cmk_base.check_utils.is_snmp_check("brocade.fan") == True
    assert cmk_base.check_utils.is_snmp_check("brocade.xy") == True
    assert cmk_base.check_utils.is_snmp_check("brocade") == True


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
