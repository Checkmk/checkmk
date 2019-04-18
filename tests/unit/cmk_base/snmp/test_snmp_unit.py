# encoding: utf-8

import pytest  # type: ignore
from testlib.base import Scenario

import cmk_base.config as config
import cmk_base.snmp as snmp


@pytest.mark.parametrize(
    "encoding,columns,expected",
    [
        (None, [(['\xc3\xbc'], "string")], [[u"ü"]]),  # utf-8
        (None, [('\xc3\xbc', "binary")], [[[195], [188]]]),  # utf-8
        (None, [(["\xfc"], "string")], [[u"ü"]]),  # latin-1
        (None, [('\xfc', "binary")], [[[252]]]),  # latin-1
        ("utf-8", [(['\xc3\xbc'], "string")], [[u"ü"]]),
        ("latin1", [(['\xfc'], "string")], [[u"ü"]]),
        ("cp437", [(['\x81'], "string")], [[u"ü"]]),
    ])
def test_sanitize_snmp_encoding(monkeypatch, encoding, columns, expected):
    monkeypatch.setattr(config, "snmp_character_encoding_of", lambda h: encoding)
    assert snmp._sanitize_snmp_encoding("localhost", columns) == expected


def test_is_bulkwalk_host(monkeypatch):
    ts = Scenario().set_ruleset("bulkwalk_hosts", [
        ([], ["localhost"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config("abc").snmp_config("").is_bulkwalk_host is False
    assert config_cache.get_host_config("localhost").snmp_config("").is_bulkwalk_host is True
