#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Parsing SNMP traps and translating their var binds"""

import logging
from collections.abc import Callable, Iterator

import pysnmp.debug  # type: ignore[import-untyped]
import pytest
from pyasn1.codec.ber import encoder
from pysnmp.proto import api, rfc1155  # type: ignore[import-untyped]
from pysnmp.proto.rfc1902 import (  # type: ignore[import-untyped]
    IpAddress,
    ObjectName,
    OctetString,
    TimeTicks,
)

from cmk.utils.log import VERBOSE

import cmk.ec.export as ec
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
    pysnmp.debug.setLogger(previous_pysnmp_logger)


@pytest.fixture(name="parser")
def fixture_parser(make_parser: MakeParser, config: Config) -> SNMPTrapParser:
    return make_parser(config)


def v1_trap(*, generic_trap: int) -> bytes:
    """An SNMPv1 trap from the "public" community, which the default configuration accepts"""
    proto = api.protoModules[api.protoVersion1]
    pdu = proto.TrapPDU()
    # Not setDefaults(), which looks up the address of the local host as the agent address.
    proto.apiTrapPDU.setEnterprise(pdu, (1, 3, 6, 1, 4, 1, 32473))
    proto.apiTrapPDU.setAgentAddr(pdu, "192.0.2.1")
    proto.apiTrapPDU.setGenericTrap(pdu, generic_trap)
    proto.apiTrapPDU.setSpecificTrap(pdu, 0)
    proto.apiTrapPDU.setTimeStamp(pdu, 0)
    proto.apiTrapPDU.setVarBinds(pdu, [])
    message = proto.Message()
    proto.apiMessage.setDefaults(message)
    proto.apiMessage.setCommunity(message, "public")
    proto.apiMessage.setPDU(message, pdu)
    trap: bytes = encoder.encode(message)
    return trap


def v2c_trap(var_binds: VarBinds) -> bytes:
    """An SNMPv2c trap from the "public" community, which the default configuration accepts"""
    proto = api.protoModules[api.protoVersion2c]
    pdu = proto.SNMPv2TrapPDU()
    proto.apiTrapPDU.setDefaults(pdu)
    proto.apiTrapPDU.setVarBinds(pdu, [*proto.apiTrapPDU.getVarBinds(pdu), *var_binds])
    message = proto.Message()
    proto.apiMessage.setDefaults(message)
    proto.apiMessage.setCommunity(message, "public")
    proto.apiMessage.setPDU(message, pdu)
    trap: bytes = encoder.encode(message)
    return trap


def test_received_trap_is_logged_with_its_sender(
    parser: SNMPTrapParser, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(VERBOSE, logger=logger.name)

    parser.parse(v2c_trap([]), ("192.0.2.1", 162))

    assert "Trap received from 192.0.2.1:162. Checking for acceptance now." in caplog.messages


def test_failed_translation_warns_about_the_oid_the_sender_and_the_error(
    translator: SNMPTrapTranslator, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    var_binds = [(UNTRANSLATABLE_OID, OctetString("hurz"))]
    caplog.set_level(logging.WARNING, logger=logger.name)

    translator.translate("192.0.2.1", var_binds)

    prefix = (
        f"Failed to translate OID {UNTRANSLATABLE_OID} in trap from 192.0.2.1, "
        "keeping it untranslated: SmiError: "
    )
    suffix = " (enable debug logging for details)"
    [error] = [
        message.removeprefix(prefix).removesuffix(suffix)
        for message in caplog.messages
        if message.startswith(prefix) and message.endswith(suffix)
    ]
    assert error  # PySNMP's message


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
(MibScalar,) = mibBuilder.importSymbols("SNMPv2-SMI", "MibScalar")
(OctetString,) = mibBuilder.importSymbols("ASN1", "OctetString")


class _TestLogName_Type(OctetString):
    defaultValue = OctetString("None")


mibBuilder.exportSymbols(
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

    assert (
        logger.name,
        logging.DEBUG,
        "receiveMessage: msgVersion 1, msg decoded",
    ) in caplog.record_tuples


def test_pysnmp_debugging_follows_the_log_level(
    make_parser: MakeParser, config: Config, logger: logging.Logger
) -> None:
    logger.setLevel(logging.DEBUG)
    make_parser(config)

    logger.setLevel(logging.INFO)

    assert not pysnmp.debug.logger & pysnmp.debug.flagAll
    assert not pysnmp.debug.flagAll & pysnmp.debug.logger


# A compiled MIB whose object can't print its values
BROKEN_MIB = """
(MibScalar,) = mibBuilder.importSymbols("SNMPv2-SMI", "MibScalar")
(OctetString,) = mibBuilder.importSymbols("ASN1", "OctetString")


class BrokenSyntax(OctetString):
    def prettyPrint(self, scope=0):
        raise RuntimeError("broken syntax")


mibBuilder.exportSymbols(
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


def test_trap_failing_after_acceptance_leaves_no_pysnmp_state_behind(
    parser: SNMPTrapParser,
) -> None:
    with pytest.raises(KeyError):  # PySNMP fails on unknown generic traps.
        parser.parse(v1_trap(generic_trap=7), ("192.0.2.1", 162))

    # PySNMP keeps the transport of each message until it has processed it.
    assert vars(parser.snmp_engine.msgAndPduDsp)["_MsgAndPduDispatcher__transportInfo"] == {}


@pytest.mark.parametrize(
    "level, with_traceback",
    [
        pytest.param(VERBOSE, False, id="verbose"),
        pytest.param(logging.DEBUG, True, id="debugging"),
    ],
)
def test_data_which_is_no_snmp_message_comes_with_a_traceback_only_when_debugging(
    parser: SNMPTrapParser,
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
    level: int,
    with_traceback: bool,
) -> None:
    logger.setLevel(level)

    parser.parse(b"hello world", ("192.0.2.1", 162))

    [dropped] = [r for r in caplog.records if "PySNMP failed on it" in r.getMessage()]
    assert bool(dropped.exc_info) == with_traceback
