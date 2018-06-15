import pytest

import cmk_base.discovery as discovery
import cmk_base.config as config
import cmk_base.check_utils
import cmk_base.check_api as check_api

def test_load_checks():
    config._initialize_data_structures()
    assert config.check_info == {}
    config.load_all_checks(check_api.get_check_api_context)
    assert len(config.check_info) > 1000


def test_is_tcp_check():
    config.load_all_checks(check_api.get_check_api_context)
    assert cmk_base.check_utils.is_tcp_check("xxx") == False
    assert cmk_base.check_utils.is_tcp_check("uptime") == True
    assert cmk_base.check_utils.is_tcp_check("uptime") == True
    assert cmk_base.check_utils.is_tcp_check("snmp_uptime") == False
    assert cmk_base.check_utils.is_tcp_check("mem") == True
    assert cmk_base.check_utils.is_tcp_check("mem.linux") == True
    assert cmk_base.check_utils.is_tcp_check("mem.ding") == True
    assert cmk_base.check_utils.is_tcp_check("apc_humidity") == False


def test_is_snmp_check():
    config.load_all_checks(check_api.get_check_api_context)
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
    config.load_all_checks(check_api.get_check_api_context)
    assert "uptime" in config.discoverable_tcp_checks()
    assert "snmp_uptime" not in config.discoverable_tcp_checks()
    assert "logwatch" in config.discoverable_tcp_checks()


@pytest.mark.parametrize("result,ruleset", [
    (False, None),
    (False, []),
    (False, [( None, [], config.ALL_HOSTS, {} )]),
    (False, [( {}, [], config.ALL_HOSTS, {} )]),
    (True, [( {"status_data_inventory": True}, [], config.ALL_HOSTS, {} )]),
    (False, [( {"status_data_inventory": False}, [], config.ALL_HOSTS, {} )]),
])
def test_do_status_data_inventory_for(monkeypatch, result, ruleset):
    config.load_default_config()

    monkeypatch.setattr(config, "all_hosts", ["abc"])
    monkeypatch.setattr(config, "active_checks", {
        "cmk_inv": ruleset,
    })

    assert config.do_status_data_inventory_for("abc") == result
