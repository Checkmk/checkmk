# pylint: disable=redefined-outer-name

import pytest  # type: ignore
from testlib.base import Scenario

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


############ Management board checks


def _check_plugins():
    return {
        "tcp_check_mgmt_only": "mgmt_only",
        "tcp_check_host_precedence": "host_precedence",
        "tcp_check_host_only": "host_only",
        "snmp_check_mgmt_only": "mgmt_only",
        "snmp_check_host_precedence": "host_precedence",
        "snmp_check_host_only": "host_only",
    }


@pytest.fixture()
def patch_mgmt_board_plugins(monkeypatch):
    monkeypatch.setattr(config, "_get_management_board_precedence",
                        lambda c, _: _check_plugins()[c])
    monkeypatch.setattr(cmk_base.check_utils, "is_snmp_check", lambda c: c.startswith("snmp_"))


############ Unknown check plugins


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,result", [
    (False, []),
    (True, []),
])
def test_filter_by_management_board_unknown_check_plugins(monkeypatch, for_discovery, result):
    ts = Scenario()
    ts.add_host("this_host")
    ts.apply(monkeypatch)

    found_check_plugins = [c for c in _check_plugins()]
    monkeypatch.setattr(config, "check_info", [])

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(result)


############ TCP host


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,result", [
    (False, ["tcp_check_host_precedence", "tcp_check_host_only"]),
    (True, ["tcp_check_host_precedence", "tcp_check_host_only"]),
])
def test_filter_by_management_board_TCP_host_without_mgmt_board(monkeypatch, for_discovery, result):
    ts = Scenario()
    ts.add_host("this_host")
    ts.apply(monkeypatch)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("tcp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(result)


############ SNMP host


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,result", [
    (False, ["snmp_check_host_precedence", "snmp_check_host_only"]),
    (True, ["snmp_check_host_precedence", "snmp_check_host_only"]),
])
def test_filter_by_management_board_SNMP_host_without_mgmt_board(monkeypatch, for_discovery,
                                                                 result):
    ts = Scenario()
    ts.add_host("this_host", tags={"snmp_ds": "snmp-v1", "agent": "no-agent"})
    ts.apply(monkeypatch)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(result)


############ Dual host


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,result", [
    (False, [
        "tcp_check_host_precedence", "tcp_check_host_only", "snmp_check_host_precedence",
        "snmp_check_host_only"
    ]),
    (True, [
        "tcp_check_host_precedence", "tcp_check_host_only", "snmp_check_host_precedence",
        "snmp_check_host_only"
    ]),
])
def test_filter_by_management_board_dual_host_without_mgmt_board(monkeypatch, for_discovery,
                                                                 result):
    ts = Scenario()
    ts.add_host("this_host", tags={"snmp_ds": "snmp-v1", "agent": "cmk-agent"})
    ts.apply(monkeypatch)

    found_check_plugins = [c for c in _check_plugins()]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(result)


############ TCP host + SNMP Management Board


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,host_result,mgmt_board_result", [
    (False, ["tcp_check_host_precedence", "tcp_check_host_only"
            ], ["snmp_check_mgmt_only", "snmp_check_host_precedence", "snmp_check_host_only"]),
    (True, ["tcp_check_host_precedence", "tcp_check_host_only"
           ], ["snmp_check_mgmt_only", "snmp_check_host_precedence"]),
])
def test_filter_by_management_board_TCP_host_with_SNMP_mgmt_board(monkeypatch, for_discovery,
                                                                  host_result, mgmt_board_result):
    ts = Scenario()
    ts.add_host("this_host", tags={
        "agent": "cmk-agent",
    })
    config_cache = ts.apply(monkeypatch)
    h = config_cache.get_host_config("this_host")
    h.has_management_board = True

    found_check_plugins = [c for c in _check_plugins() if c.startswith("tcp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(host_result)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             True,
                                             for_discovery=for_discovery) == set(mgmt_board_result)


############ SNMP host + SNMP Management Board


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,host_result,mgmt_board_result", [
    (False, ["snmp_check_host_only", "snmp_check_host_precedence"], ["snmp_check_mgmt_only"]),
    (True, ["snmp_check_host_only", "snmp_check_host_precedence"], ["snmp_check_mgmt_only"]),
])
def test_filter_by_management_board_SNMP_host_with_SNMP_mgmt_board(monkeypatch, for_discovery,
                                                                   host_result, mgmt_board_result):
    ts = Scenario()
    ts.add_host("this_host", tags={"snmp_ds": "snmp-v1", "agent": "no-agent"})
    config_cache = ts.apply(monkeypatch)
    h = config_cache.get_host_config("this_host")
    h.has_management_board = True

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(host_result)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             True,
                                             for_discovery=for_discovery) == set(mgmt_board_result)


############ Dual host + SNMP Management Board


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,host_result,mgmt_board_result", [
    (False, [
        "tcp_check_host_precedence", "tcp_check_host_only", "snmp_check_host_only",
        "snmp_check_host_precedence"
    ], ["snmp_check_mgmt_only"]),
    (True, [
        "tcp_check_host_precedence", "tcp_check_host_only", "snmp_check_host_only",
        "snmp_check_host_precedence"
    ], ["snmp_check_mgmt_only"]),
])
def test_filter_by_management_board_dual_host_with_SNMP_mgmt_board(monkeypatch, for_discovery,
                                                                   host_result, mgmt_board_result):
    ts = Scenario()
    ts.add_host("this_host", tags={"snmp_ds": "snmp-v1", "agent": "cmk-agent"})
    config_cache = ts.apply(monkeypatch)
    h = config_cache.get_host_config("this_host")
    h.has_management_board = True

    found_check_plugins = [c for c in _check_plugins()]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(host_result)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             True,
                                             for_discovery=for_discovery) == set(mgmt_board_result)
