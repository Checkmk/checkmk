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
from pysnmp.proto import api  # type: ignore[import-untyped]

from cmk.utils.log import VERBOSE

import cmk.ec.export as ec
from cmk.ec.config import Config
from cmk.ec.snmp import SNMPTrapParser, VarBinds

type MakeParser = Callable[[Config], SNMPTrapParser]


@pytest.fixture(name="make_parser")
def fixture_make_parser(settings: ec.Settings, logger: logging.Logger) -> Iterator[MakeParser]:
    """Parsers for the given configuration, restoring PySNMP's global logger afterwards"""
    previous_pysnmp_logger = pysnmp.debug.logger
    yield lambda config: SNMPTrapParser(settings, config, logger)
    pysnmp.debug.setLogger(previous_pysnmp_logger)


@pytest.fixture(name="parser")
def fixture_parser(make_parser: MakeParser, config: Config) -> SNMPTrapParser:
    return make_parser(config)


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
