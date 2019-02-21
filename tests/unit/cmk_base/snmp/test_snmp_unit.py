# encoding: utf-8

import pytest
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
    monkeypatch.setattr(config, "bulkwalk_hosts", [
        ([], ["localhost"], {}),
    ])
    assert config.is_bulkwalk_host("abc") is False
    assert config.is_bulkwalk_host("localhost") is True
