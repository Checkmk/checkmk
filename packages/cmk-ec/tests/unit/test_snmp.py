#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Parsing SNMP traps and translating their var binds"""

import logging
from collections.abc import Callable, Iterator

import pysnmp.debug
import pysnmp.entity.config
import pysnmp.entity.engine
import pytest
from pyasn1.codec.ber import encoder
from pysnmp.proto import api, rfc1155, rfc3411
from pysnmp.proto.mpmod.rfc3412 import SNMPv3Message
from pysnmp.proto.rfc1902 import IpAddress, ObjectName, OctetString, TimeTicks
from pysnmp.proto.secmod.rfc3414.service import UsmSecurityParameters

import cmk.ec.export as ec
from cmk.ccc.log import VERBOSE
from cmk.ec.config import Config, SNMPCredentials
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


def v1_trap(*, time_stamp: int = 0, generic_trap: int = 0) -> bytes:
    """An SNMPv1 trap from the "public" community, which the default configuration accepts"""
    proto = api.PROTOCOL_MODULES[api.SNMP_VERSION_1]
    pdu = proto.TrapPDU()
    # Not set_defaults(), which looks up the address of the local host as the agent address.
    proto.apiTrapPDU.set_enterprise(pdu, (1, 3, 6, 1, 4, 1, 32473))
    proto.apiTrapPDU.set_agent_address(pdu, "192.0.2.1")
    proto.apiTrapPDU.set_generic_trap(pdu, generic_trap)
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


def v2c_trap(var_binds: VarBinds, *, community: str = "public") -> bytes:
    """An SNMPv2c trap, by default from "public", which the default configuration accepts"""
    proto = api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]
    pdu = proto.SNMPv2TrapPDU()
    proto.apiTrapPDU.set_defaults(pdu)
    proto.apiTrapPDU.set_varbinds(pdu, [*proto.apiTrapPDU.get_varbinds(pdu), *var_binds])
    message = proto.Message()
    proto.apiMessage.set_defaults(message)
    proto.apiMessage.set_community(message, community)
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


def v3_message(
    pdu_type: str,
    *,
    engine_id: bytes,
    user: bytes = b"",
    auth_flag: bool = False,
    priv_flag: bool = False,
    boots: int = 0,
    encrypted_pdu: bytes | None = None,
) -> bytes:
    """An unauthenticated SNMPv3 message, built by hand for users and engines PySNMP doesn't know"""
    proto = api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]
    pdu = getattr(proto, pdu_type)()
    proto.apiPDU.set_defaults(pdu)
    security_parameters = UsmSecurityParameters()
    security_parameters["msgAuthoritativeEngineId"] = engine_id
    security_parameters["msgAuthoritativeEngineBoots"] = boots
    security_parameters["msgAuthoritativeEngineTime"] = 0
    security_parameters["msgUserName"] = user
    security_parameters["msgAuthenticationParameters"] = b""
    security_parameters["msgPrivacyParameters"] = b""
    message = SNMPv3Message()
    message["msgVersion"] = 3
    message["msgGlobalData"]["msgID"] = 4711
    message["msgGlobalData"]["msgMaxSize"] = 65507
    # Requests are reportable, other PDUs aren't.
    reportable = pdu.tagSet in rfc3411.CONFIRMED_CLASS_PDUS
    flags = (0x04 if reportable else 0x00) | (0x01 if auth_flag else 0x00)
    flags |= 0x02 if priv_flag else 0x00
    message["msgGlobalData"]["msgFlags"] = bytes([flags])
    message["msgGlobalData"]["msgSecurityModel"] = 3
    message["msgSecurityParameters"] = encoder.encode(security_parameters)
    if encrypted_pdu is None:
        scoped_pdu = message["msgData"]["plaintext"]
        scoped_pdu["contextEngineId"] = engine_id
        scoped_pdu["contextName"] = b""
        scoped_pdu["data"].setComponentByType(
            pdu.tagSet, pdu, verifyConstraints=False, matchTags=False, matchConstraints=False
        )
    else:
        message["msgData"]["encryptedPDU"] = encrypted_pdu
    data: bytes = encoder.encode(message)
    return data


def test_snmpv3_requests_are_dropped_without_failing(
    parser: SNMPTrapParser, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    logger.setLevel(VERBOSE)

    # PySNMP answers them with a discovery report.
    result = parser.parse(v3_message("GetRequestPDU", engine_id=b""), ("192.0.2.1", 162))

    assert (result, [m for m in caplog.messages if "PySNMP failed on it" in m]) == (None, [])


def test_snmpv3_report_senders_are_forgotten(parser: SNMPTrapParser) -> None:
    # PySNMP accepts them for its empty discovery user and caches the sender.
    parser.parse(
        v3_message("ReportPDU", engine_id=bytes.fromhex("8000000001020304")), ("192.0.2.1", 162)
    )

    # PySNMP keeps them for 300 s of 0.1 s ticks, i.e. 3000 messages here.
    for _ in range(3000):
        parser.parse(b"", ("192.0.2.1", 162))

    message_processing = vars(parser.snmp_engine.message_processing_subsystems[3])  # type: ignore[index]
    security_model = vars(parser.snmp_engine.security_models[3])
    assert (
        message_processing["_SnmpV3MessageProcessingModel__engineIdCache"],
        security_model["_SnmpUSMSecurityModel__timeline"],
    ) == ({}, {})


@pytest.mark.parametrize(
    "message",
    [
        pytest.param(
            v3_message("SNMPv2TrapPDU", engine_id=b"", encrypted_pdu=b"\x01\x02\x03"),
            id="discovery-encrypted",
        ),
        pytest.param(
            v3_message(
                "SNMPv2TrapPDU",
                engine_id=bytes.fromhex("8000000001020304"),
                encrypted_pdu=b"\x01\x02\x03",
            ),
            id="empty-user-encrypted",
        ),
        pytest.param(
            v3_message(
                "SNMPv2TrapPDU",
                engine_id=bytes.fromhex("8000000001020304"),
                auth_flag=True,
                boots=2**31 - 1,
            ),
            id="empty-user-flagged-authNoPriv-at-the-last-boot",
        ),
    ],
)
def test_snmpv3_messages_pysnmp_fails_on_leave_no_pysnmp_state_behind(
    parser: SNMPTrapParser, message: bytes
) -> None:
    parser.parse(message, ("192.0.2.1", 162))

    security_models = parser.snmp_engine.security_models.values()
    assert all(model._cache.is_empty() for model in security_models)  # type: ignore[no-untyped-call]  # noqa: SLF001


def test_trap_failing_after_acceptance_leaves_no_pysnmp_state_behind(
    parser: SNMPTrapParser,
) -> None:
    with pytest.raises(KeyError):  # PySNMP fails on unknown generic traps.
        parser.parse(v1_trap(generic_trap=7), ("192.0.2.1", 162))

    # PySNMP keeps the transport of each message until it has processed it.
    assert vars(parser.snmp_engine.message_dispatcher)["_MsgAndPduDispatcher__transportInfo"] == {}


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


class CapturingTransportDispatcher:
    """Keeps what a PySNMP engine sends instead of sending it"""

    def __init__(self) -> None:
        self.messages: list[bytes] = []

    def send_message(self, message: bytes, *_: object) -> None:
        self.messages.append(bytes(message))


SENDER_ENGINE_ID = "80001f8803525400123456"


def v3_trap(user: str, *, auth_key: str | None = None) -> bytes:
    """An SNMPv3 trap of the given user from SENDER_ENGINE_ID, authenticated via SHA with a key"""
    sender = pysnmp.entity.engine.SnmpEngine(snmpEngineID=OctetString(hexValue=SENDER_ENGINE_ID))
    if auth_key is None:
        pysnmp.entity.config.add_v3_user(sender, user)
    else:
        pysnmp.entity.config.add_v3_user(
            sender, user, pysnmp.entity.config.USM_AUTH_HMAC96_SHA, auth_key
        )
    transport_dispatcher = CapturingTransportDispatcher()
    sender.transport_dispatcher = transport_dispatcher  # type: ignore[assignment]
    proto = api.PROTOCOL_MODULES[api.SNMP_VERSION_2C]
    pdu = proto.SNMPv2TrapPDU()
    proto.apiTrapPDU.set_defaults(pdu)
    sender.message_dispatcher.send_pdu(
        snmpEngine=sender,
        transportDomain=(1, 3, 6, 1, 6, 1, 1),
        transportAddress=("192.0.2.1", 162),
        messageProcessingModel=3,
        securityModel=3,
        securityName=OctetString(user),
        securityLevel=1 if auth_key is None else 2,
        contextEngineId=sender.snmpEngineID,
        contextName=b"",
        pduVersion=1,
        PDU=pdu,
        expectResponse=False,
    )
    [message] = transport_dispatcher.messages
    return message


def test_snmpv2c_trap_of_an_unknown_community_is_dropped_naming_version_and_community(
    parser: SNMPTrapParser, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    logger.setLevel(VERBOSE)

    parser.parse(v2c_trap([], community="nope"), ("192.0.2.1", 162))

    assert "Trap (v2c) dropped from 192.0.2.1: Unknown community (nope)" in caplog.messages


def test_snmpv3_trap_of_an_unknown_user_is_dropped_naming_version_and_user(
    parser: SNMPTrapParser, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    logger.setLevel(VERBOSE)

    parser.parse(v3_trap("sally"), ("192.0.2.1", 162))

    assert (
        "Trap (v3) dropped from 192.0.2.1: Unknown credentials (msgUserName: sally)"
        in caplog.messages
    )


def test_snmpv3_trap_failing_authentication_is_dropped_naming_version_and_reason(
    make_parser: MakeParser,
    config: Config,
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger.setLevel(VERBOSE)
    parser = make_parser(
        config
        | {
            "snmp_credentials": [
                {
                    "description": "",
                    "credentials": ("authNoPriv", "sha", "harry", "right-key"),
                    "engine_ids": [SENDER_ENGINE_ID],
                }
            ]
        }
    )

    parser.parse(v3_trap("harry", auth_key="wrong-key"), ("192.0.2.1", 162))

    assert "Trap (v3) dropped from 192.0.2.1: Authenticator mismatched" in caplog.messages


@pytest.mark.parametrize(
    "message, dropped",
    [
        pytest.param(
            v2c_trap([], community="x\ny"),
            "Trap (v2c) dropped from 192.0.2.1: Unknown community (0x780a79)",
            id="community",
        ),
        pytest.param(
            v3_message("SNMPv2TrapPDU", engine_id=bytes.fromhex(SENDER_ENGINE_ID), user=b"x\ny"),
            "Trap (v3) dropped from 192.0.2.1: Unknown credentials (msgUserName: 0x780a79)",
            id="user",
        ),
    ],
)
def test_dropped_traps_show_names_with_control_characters_in_hex(
    parser: SNMPTrapParser,
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
    message: bytes,
    dropped: str,
) -> None:
    logger.setLevel(VERBOSE)

    parser.parse(message, ("192.0.2.1", 162))

    assert dropped in caplog.messages


def request(version: int, pdu_type: str, *, community: str = "public") -> bytes:
    """An SNMPv1/v2c request, by default from "public", which the default configuration accepts"""
    proto = api.PROTOCOL_MODULES[version]
    pdu = getattr(proto, pdu_type)()
    proto.apiPDU.set_defaults(pdu)
    message = proto.Message()
    proto.apiMessage.set_defaults(message)
    proto.apiMessage.set_community(message, community)
    proto.apiMessage.set_pdu(message, pdu)
    data: bytes = encoder.encode(message)
    return data


@pytest.mark.parametrize(
    "version, pdu_type",
    [
        pytest.param(api.SNMP_VERSION_1, "GetRequestPDU", id="v1-get"),
        pytest.param(api.SNMP_VERSION_1, "SetRequestPDU", id="v1-set"),
        pytest.param(api.SNMP_VERSION_2C, "GetRequestPDU", id="v2c-get"),
        pytest.param(api.SNMP_VERSION_2C, "GetNextRequestPDU", id="v2c-getnext"),
        pytest.param(api.SNMP_VERSION_2C, "GetBulkRequestPDU", id="v2c-getbulk"),
        pytest.param(api.SNMP_VERSION_2C, "SetRequestPDU", id="v2c-set"),
        pytest.param(api.SNMP_VERSION_2C, "InformRequestPDU", id="v2c-inform"),
    ],
)
def test_requests_leave_no_pysnmp_state_behind(
    parser: SNMPTrapParser, version: int, pdu_type: str
) -> None:
    parser.parse(request(version, pdu_type), ("192.0.2.1", 162))

    # PySNMP's security models keep the state of each request for its response.
    security_models = parser.snmp_engine.security_models.values()
    assert all(model._cache.is_empty() for model in security_models)  # type: ignore[no-untyped-call]  # noqa: SLF001


@pytest.mark.parametrize(
    "version, pdu_type, dropped",
    [
        pytest.param(api.SNMP_VERSION_1, "GetRequestPDU", "GetRequest (v1)", id="v1-get"),
        pytest.param(
            api.SNMP_VERSION_2C, "InformRequestPDU", "InformRequest (v2c)", id="v2c-inform"
        ),
    ],
)
def test_requests_are_dropped_naming_their_type_and_version(
    parser: SNMPTrapParser,
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
    version: int,
    pdu_type: str,
    dropped: str,
) -> None:
    logger.setLevel(VERBOSE)

    parser.parse(request(version, pdu_type), ("192.0.2.1", 162))

    assert f"{dropped} dropped from 192.0.2.1, only traps are supported" in caplog.messages


@pytest.mark.parametrize(
    "pdu_type, name",
    [
        pytest.param("GetRequestPDU", "GetRequest", id="get"),
        pytest.param("InformRequestPDU", "InformRequest", id="inform"),
        pytest.param("ReportPDU", "Report", id="report"),
        pytest.param("SNMPv2TrapPDU", "Trap", id="trap"),
    ],
)
def test_snmpv3_messages_of_an_unknown_engine_are_dropped_naming_their_type(
    parser: SNMPTrapParser,
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
    pdu_type: str,
    name: str,
) -> None:
    logger.setLevel(VERBOSE)

    parser.parse(v3_message(pdu_type, engine_id=b""), ("192.0.2.1", 162))

    [dropped] = [message for message in caplog.messages if " dropped from " in message]
    assert dropped == f"{name} (v3) dropped from 192.0.2.1: Unknown SNMP engine ID encountered"


@pytest.mark.parametrize(
    "version, pdu_type, name",
    [
        pytest.param(api.SNMP_VERSION_1, "GetRequestPDU", "GetRequest (v1)", id="v1-get"),
        pytest.param(
            api.SNMP_VERSION_2C, "InformRequestPDU", "InformRequest (v2c)", id="v2c-inform"
        ),
    ],
)
def test_requests_of_an_unknown_community_are_dropped_naming_their_type(
    parser: SNMPTrapParser,
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
    version: int,
    pdu_type: str,
    name: str,
) -> None:
    logger.setLevel(VERBOSE)

    parser.parse(request(version, pdu_type, community="nope"), ("192.0.2.1", 162))

    assert f"{name} dropped from 192.0.2.1: Unknown community (nope)" in caplog.messages


@pytest.mark.parametrize(
    "pdu_type, name",
    [
        pytest.param("GetRequestPDU", "GetRequest", id="get"),
        pytest.param("ReportPDU", "Report", id="report"),
    ],
)
def test_snmpv3_messages_of_an_unknown_user_are_dropped_naming_their_type(
    parser: SNMPTrapParser,
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
    pdu_type: str,
    name: str,
) -> None:
    logger.setLevel(VERBOSE)

    parser.parse(
        v3_message(pdu_type, engine_id=bytes.fromhex(SENDER_ENGINE_ID), user=b"sally"),
        ("192.0.2.1", 162),
    )

    [dropped] = [message for message in caplog.messages if " dropped from " in message]
    assert (
        dropped == f"{name} (v3) dropped from 192.0.2.1: Unknown credentials (msgUserName: sally)"
    )


def test_encrypted_snmpv3_traps_are_dropped_as_messages(
    parser: SNMPTrapParser, logger: logging.Logger, caplog: pytest.LogCaptureFixture
) -> None:
    logger.setLevel(VERBOSE)

    parser.parse(
        v3_message(
            "SNMPv2TrapPDU",
            engine_id=bytes.fromhex(SENDER_ENGINE_ID),
            user=b"sally",
            auth_flag=True,
            priv_flag=True,
            encrypted_pdu=b"\x01\x02\x03",
        ),
        ("192.0.2.1", 162),
    )

    [dropped] = [message for message in caplog.messages if " dropped from " in message]
    assert (
        dropped == "Message (v3) dropped from 192.0.2.1: Unknown credentials (msgUserName: sally)"
    )


def snmpv3_config(config: Config, credentials: SNMPCredentials) -> Config:
    """The configuration with only the given SNMPv3 credentials, for SENDER_ENGINE_ID"""
    return config | {
        "snmp_credentials": [
            {"description": "", "credentials": credentials, "engine_ids": [SENDER_ENGINE_ID]}
        ]
    }


@pytest.mark.parametrize(
    "credentials, auth_key",
    [
        pytest.param(("noAuthNoPriv", "harry"), None, id="noAuthNoPriv"),
        pytest.param(("authNoPriv", "sha", "harry", "right-key"), "right-key", id="authNoPriv"),
        pytest.param(
            ("authPriv", "sha", "harry", "right-key", "AES", "priv-key"),
            "right-key",
            id="authPriv-sending-authNoPriv",
        ),
    ],
)
def test_snmpv3_trap_of_a_configured_user_is_accepted(
    make_parser: MakeParser, config: Config, credentials: SNMPCredentials, auth_key: str | None
) -> None:
    parser = make_parser(snmpv3_config(config, credentials))

    result = parser.parse(v3_trap("harry", auth_key=auth_key), ("192.0.2.1", 162))

    assert result is not None


@pytest.mark.parametrize(
    "credentials",
    [
        pytest.param(("authNoPriv", "sha", "harry", "right-key"), id="authNoPriv"),
        pytest.param(("authPriv", "sha", "harry", "right-key", "AES", "priv-key"), id="authPriv"),
    ],
)
def test_unauthenticated_snmpv3_trap_of_a_user_with_authentication_is_dropped(
    make_parser: MakeParser,
    config: Config,
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
    credentials: SNMPCredentials,
) -> None:
    parser = make_parser(snmpv3_config(config, credentials))
    logger.setLevel(VERBOSE)

    result = parser.parse(v3_trap("harry"), ("192.0.2.1", 162))

    assert (result, [m for m in caplog.messages if " dropped from " in m]) == (
        None,
        ["Trap (v3) dropped from 192.0.2.1: Authentication missing (msgUserName: harry)"],
    )


@pytest.mark.parametrize(
    "auth_flag",
    [
        pytest.param(False, id="noAuthNoPriv"),
        # PySNMP doesn't authenticate it, but reports authNoPriv.
        pytest.param(True, id="flagged-authNoPriv"),
    ],
)
def test_snmpv3_trap_of_the_empty_user_is_dropped(
    make_parser: MakeParser,
    config: Config,
    logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
    auth_flag: bool,
) -> None:
    parser = make_parser(snmpv3_config(config, ("authNoPriv", "sha", "harry", "right-key")))
    logger.setLevel(VERBOSE)

    result = parser.parse(
        v3_message("SNMPv2TrapPDU", engine_id=bytes.fromhex(SENDER_ENGINE_ID), auth_flag=auth_flag),
        ("192.0.2.1", 162),
    )

    assert (result, [m for m in caplog.messages if " dropped from " in m]) == (
        None,
        ["Trap (v3) dropped from 192.0.2.1: Unknown credentials (msgUserName: )"],
    )
