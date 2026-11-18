#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Parsing SNMP traps and translating their var binds"""

import logging
from collections.abc import Callable, Iterator

import pysnmp.debug
import pytest
from pyasn1.codec.ber import encoder
from pysnmp.proto import api, rfc1155
from pysnmp.proto.rfc1902 import IpAddress, ObjectName, OctetString, TimeTicks

import cmk.ec.export as ec
from cmk.ccc.log import VERBOSE
from cmk.ec.config import Config
from cmk.ec.snmp import SNMPTrapParser, SNMPTrapTranslator, VarBinds

# sysORDescr.1.2, but sysORTable has only one index.
UNTRANSLATABLE_OID = ObjectName("1.3.6.1.2.1.1.9.1.3.1.2")

UTF_8_TEXT = "Lüfter groß".encode()  # ß contains 0x9f, a C1 control character in Latin-1.
UTF_16_TEXT = "Link down".encode("utf-16-le")  # Every other byte is a NUL.

type MakeParser = Callable[[Config], SNMPTrapParser]


@pytest.fixture(name="translator")
def fixture_translator(
    settings: ec.Settings, config: Config, logger: logging.Logger
) -> SNMPTrapTranslator:
    return SNMPTrapTranslator(settings, config | {"translate_snmptraps": (True, {})}, logger)


@pytest.fixture(name="make_parser")
def fixture_make_parser(settings: ec.Settings, logger: logging.Logger) -> Iterator[MakeParser]:
    """Parsers for the given configuration, restoring PySNMP's global logger afterwards"""
    previous_pysnmp_logger = pysnmp.debug.logger
    yield lambda config: SNMPTrapParser(settings, config, logger)
    pysnmp.debug.set_logger(previous_pysnmp_logger)  # type: ignore[no-untyped-call]


@pytest.fixture(name="parser")
def fixture_parser(make_parser: MakeParser, config: Config) -> SNMPTrapParser:
    return make_parser(config)


def v1_trap(time_stamp: int) -> bytes:
    """An SNMPv1 trap from the "public" community, which the default configuration accepts"""
    proto = api.PROTOCOL_MODULES[api.SNMP_VERSION_1]
    pdu = proto.TrapPDU()
    # Not set_defaults(), which looks up the address of the local host as the agent address.
    proto.apiTrapPDU.set_enterprise(pdu, (1, 3, 6, 1, 4, 1, 32473))
    proto.apiTrapPDU.set_agent_address(pdu, "192.0.2.1")
    proto.apiTrapPDU.set_generic_trap(pdu, "coldStart")
    proto.apiTrapPDU.set_specific_trap(pdu, 0)
    proto.apiTrapPDU.set_timestamp(pdu, time_stamp)
    proto.apiTrapPDU.set_varbinds(pdu, [])
    message = proto.Message()
    proto.apiMessage.set_defaults(message)
    proto.apiMessage.set_community(message, "public")
    proto.apiMessage.set_pdu(message, pdu)
    trap: bytes = encoder.encode(message)
    return trap


def test_untranslated_snmpv1_trap_shows_its_time_stamp_as_uptime(parser: SNMPTrapParser) -> None:
    trap = v1_trap(time_stamp=123456)

    result = parser.parse(trap, ("192.0.2.1", 162))

    assert result is not None
    assert ("Uptime", "20 m") in result[0]


def v2c_trap(var_binds: VarBinds) -> bytes:
    """An SNMPv2c trap from the "public" community, which the default configuration accepts"""
    proto = api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]
    pdu = proto.SNMPv2TrapPDU()
    proto.apiTrapPDU.set_defaults(pdu)
    proto.apiTrapPDU.set_varbinds(pdu, [*proto.apiTrapPDU.get_varbinds(pdu), *var_binds])
    message = proto.Message()
    proto.apiMessage.set_defaults(message)
    proto.apiMessage.set_community(message, "public")
    proto.apiMessage.set_pdu(message, pdu)
    trap: bytes = encoder.encode(message)
    return trap


def test_trap_details_show_the_oids_types_and_values_of_the_var_binds(
    parser: SNMPTrapParser, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    if_phys_address = ObjectName("1.3.6.1.2.1.2.2.1.6.1")
    trap = v2c_trap([(if_phys_address, OctetString(b"\x00\x1a\x2b\x3c\x4d\x5e"))])
    caplog.set_level(VERBOSE, logger=logger.name)

    parser.parse(trap, ("192.0.2.1", 162))

    assert f"{if_phys_address!s:<40} = OctetString 0x001a2b3c4d5e" in caplog.messages


def test_failed_translation_warns_about_the_oid_the_sender_and_the_error(
    translator: SNMPTrapTranslator, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    var_binds = [(UNTRANSLATABLE_OID, OctetString("hurz"))]
    caplog.set_level(logging.WARNING, logger=logger.name)

    translator.translate("192.0.2.1", var_binds)

    assert any(
        message.startswith(
            f"Failed to translate OID {UNTRANSLATABLE_OID} in trap from 192.0.2.1, "
            "keeping it untranslated: SmiError: "  # followed by PySNMP's message
        )
        and message.endswith(" (enable debug logging for details)")
        for message in caplog.messages
    )


@pytest.mark.parametrize(
    "value, rendered",
    [
        # All 4 bytes are printable in Latin-1.
        pytest.param(IpAddress("198.51.100.42"), "198.51.100.42", id="IP address"),
        pytest.param(
            rfc1155.IpAddress("198.51.100.42"), "198.51.100.42", id="SNMPv1 agent address"
        ),
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


def test_failed_translation_logs_the_traceback_with_the_oid(
    translator: SNMPTrapTranslator, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    var_binds = [(UNTRANSLATABLE_OID, OctetString("hurz"))]
    caplog.set_level(logging.DEBUG, logger=logger.name)

    translator.translate("192.0.2.1", var_binds)

    assert (
        f"Failed to translate OID {UNTRANSLATABLE_OID}\nTraceback (most recent call last):"
        in caplog.text
    )


# What pysmi compiles for an OCTET STRING object with DEFVAL { "None" }, trimmed
STRING_DEFVAL_MIB = """
(MibScalar,) = mibBuilder.import_symbols("SNMPv2-SMI", "MibScalar")
(OctetString,) = mibBuilder.import_symbols("ASN1", "OctetString")


class _TestLogName_Type(OctetString):
    defaultValue = OctetString("None")


mibBuilder.export_symbols(
    "TEST-MIB", testLogName=MibScalar((1, 3, 6, 1, 4, 1, 99999, 1), _TestLogName_Type())
)
"""


def add_compiled_mib(settings: ec.Settings, name: str, code: str) -> None:
    settings.paths.compiled_mibs_dir.value.mkdir(parents=True, exist_ok=True)
    (settings.paths.compiled_mibs_dir.value / f"{name}.py").write_text(code)


@pytest.mark.parametrize(
    "level",
    [
        pytest.param(logging.INFO, id="informational"),
        pytest.param(logging.DEBUG, id="debugging"),
    ],
)
def test_variables_with_string_default_values_are_translated(
    make_parser: MakeParser,
    settings: ec.Settings,
    config: Config,
    logger: logging.Logger,
    level: int,
) -> None:
    add_compiled_mib(settings, "TEST-MIB", STRING_DEFVAL_MIB)
    logger.setLevel(level)
    parser = make_parser(config | {"translate_snmptraps": (True, {})})

    result = parser.parse(
        v2c_trap([(ObjectName("1.3.6.1.4.1.99999.1"), OctetString("backup.log"))]),
        ("192.0.2.1", 162),
    )

    assert result is not None
    assert ("TEST-MIB::testLogName", "backup.log") in result[0]


def test_pysnmp_debug_messages_are_logged_when_debugging(
    parser: SNMPTrapParser, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    logger.setLevel(logging.DEBUG)

    parser.parse(v2c_trap([]), ("192.0.2.1", 162))

    assert "receiveMessage: msgVersion 1, msg decoded" in caplog.messages


def test_pysnmp_debugging_follows_the_log_level(
    make_parser: MakeParser, config: Config, logger: logging.Logger
) -> None:
    logger.setLevel(logging.DEBUG)
    make_parser(config)

    logger.setLevel(logging.INFO)

    assert not pysnmp.debug.logger
    assert not pysnmp.debug.logger & pysnmp.debug.FLAG_ALL
    assert not pysnmp.debug.FLAG_ALL & pysnmp.debug.logger


def test_pysnmp_debugging_is_on_while_debugging(
    make_parser: MakeParser, config: Config, logger: logging.Logger
) -> None:
    logger.setLevel(logging.INFO)
    make_parser(config)

    logger.setLevel(logging.DEBUG)

    assert pysnmp.debug.logger


# A compiled MIB whose object can't print its values
BROKEN_MIB = """
(MibScalar,) = mibBuilder.import_symbols("SNMPv2-SMI", "MibScalar")
(OctetString,) = mibBuilder.import_symbols("ASN1", "OctetString")


class BrokenSyntax(OctetString):
    def prettyPrint(self, scope=0):
        raise RuntimeError("broken syntax")


mibBuilder.export_symbols(
    "BROKEN-MIB", brokenObject=MibScalar((1, 3, 6, 1, 4, 1, 99999, 2), BrokenSyntax())
)
"""


def test_failed_translation_keeps_the_variable_for_any_error(
    settings: ec.Settings, config: Config, logger: logging.Logger
) -> None:
    add_compiled_mib(settings, "BROKEN-MIB", BROKEN_MIB)
    translator = SNMPTrapTranslator(settings, config | {"translate_snmptraps": (True, {})}, logger)

    var_binds = translator.translate(
        "192.0.2.1", [(ObjectName("1.3.6.1.4.1.99999.2"), OctetString("backup.log"))]
    )

    assert var_binds == [("1.3.6.1.4.1.99999.2", "backup.log")]
