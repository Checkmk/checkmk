import pytest

import cmk_base.data_sources.abstract
import cmk_base.data_sources.snmp
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
def test_mgmt_board_data_source_management_board_ipaddress(monkeypatch, result, address, resolvable):
    source = cmk_base.data_sources.snmp.SNMPManagementBoardDataSource("hostname", "ipaddress")

    if resolvable:
        monkeypatch.setattr(ip_lookup, "lookup_ip_address", lambda h: "127.0.1.1")
    else:
        def raise_exc(h):
            raise cmk_base.exceptions.MKIPAddressLookupError("Failed to...")
        monkeypatch.setattr(ip_lookup, "lookup_ip_address", raise_exc)

    monkeypatch.setattr(config, "management_address_of", lambda h: address)
    assert source._management_board_ipaddress("hostname") == result
