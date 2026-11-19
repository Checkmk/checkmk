#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Translating the var binds of SNMP traps"""

import logging

import pytest
from pysnmp.proto import rfc1155
from pysnmp.proto.rfc1902 import IpAddress, ObjectName, OctetString, TimeTicks

import cmk.ec.export as ec
from cmk.ec.config import Config
from cmk.ec.snmp import SNMPTrapTranslator

# sysORDescr.1.2, but sysORTable has only one index.
UNTRANSLATABLE_OID = ObjectName("1.3.6.1.2.1.1.9.1.3.1.2")

UTF_8_TEXT = "Lüfter groß".encode()  # ß contains 0x9f, a C1 control character in Latin-1.
UTF_16_TEXT = "Link down".encode("utf-16-le")  # Every other byte is a NUL.


@pytest.fixture(name="translator")
def fixture_translator(
    settings: ec.Settings, config: Config, logger: logging.Logger
) -> SNMPTrapTranslator:
    return SNMPTrapTranslator(settings, config | {"translate_snmptraps": (True, {})}, logger)


def test_failed_translation_warns_about_the_oid_and_the_sender(
    translator: SNMPTrapTranslator, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    var_binds = [(UNTRANSLATABLE_OID, OctetString("hurz"))]
    caplog.set_level(logging.WARNING, logger=logger.name)

    translator.translate("192.0.2.1", var_binds)

    assert (
        f"Failed to translate OID {UNTRANSLATABLE_OID} in trap from 192.0.2.1 "
        "(enable debug logging for details)" in caplog.messages
    )


@pytest.mark.parametrize(
    "value, rendered",
    [
        # All 4 bytes are printable in Latin-1.
        pytest.param(IpAddress("198.51.100.42"), "198.51.100.42", id="IP address"),
        pytest.param(rfc1155.IpAddress("198.51.100.42"), "198.51.100.42", id="SNMPv1 IP address"),
        pytest.param(OctetString(b"\x00\x1a\x2b"), "0x001a2b", id="binary data"),
    ],
)
def test_failed_translation_pretty_prints_garbled_values(
    translator: SNMPTrapTranslator, value: OctetString | rfc1155.IpAddress, rendered: str
) -> None:
    var_binds = [(UNTRANSLATABLE_OID, value)]

    assert translator.translate("192.0.2.1", var_binds) == [(str(UNTRANSLATABLE_OID), rendered)]


@pytest.mark.parametrize(
    "value, rendered",
    [
        pytest.param(OctetString("Tür\t3\r\n".encode("latin-1")), "Tür\t3\r\n", id="Latin-1 text"),
        pytest.param(OctetString(UTF_8_TEXT), UTF_8_TEXT.decode("latin-1"), id="UTF-8 text"),
        pytest.param(OctetString(UTF_16_TEXT), UTF_16_TEXT.decode("latin-1"), id="UTF-16 text"),
        pytest.param(OctetString(b"Link down\x00"), "Link down\x00", id="NUL-terminated text"),
        pytest.param(OctetString(b"\x01a\x00b\x02"), "\x01a\x00b\x02", id="NUL, SOH, STX"),
        pytest.param(OctetString(b"\x00\x00"), "\x00\x00", id="all NULs"),
        pytest.param(TimeTicks(4200), "4200", id="time ticks"),
    ],
)
def test_failed_translation_keeps_values_without_other_control_characters_as_before(
    translator: SNMPTrapTranslator, value: OctetString | TimeTicks, rendered: str
) -> None:
    var_binds = [(UNTRANSLATABLE_OID, value)]

    assert translator.translate("192.0.2.1", var_binds) == [(str(UNTRANSLATABLE_OID), rendered)]
