#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import logging

import pytest
from pyasn1.codec.ber import encoder
from pysnmp.proto.api import v1

from cmk.ec.config import Config
from cmk.ec.history_file import FileHistory
from cmk.ec.main import EventServer


def _snmpv1_trap(generic_trap: int) -> bytes:
    """An SNMPv1 trap of the default community, PySNMP fails on unknown generic traps"""
    pdu = v1.TrapPDU()
    # Not set_defaults(), which looks up the address of the local host as the agent address.
    v1.apiTrapPDU.set_enterprise(pdu, (1, 3, 6, 1, 4, 1, 32473))
    v1.apiTrapPDU.set_agent_address(pdu, "192.0.2.1")
    v1.apiTrapPDU.set_generic_trap(pdu, generic_trap)
    v1.apiTrapPDU.set_specific_trap(pdu, 0)
    v1.apiTrapPDU.set_timestamp(pdu, 0)
    v1.apiTrapPDU.set_varbinds(pdu, [])
    message = v1.Message()
    v1.apiMessage.set_defaults(message)
    v1.apiMessage.set_community(message, "public")
    v1.apiMessage.set_pdu(message, pdu)
    return bytes(encoder.encode(message))


def test_traps_are_ignored_without_a_trap_endpoint(
    event_server: EventServer, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="cmk.mkeventd.EventServer")

    events = list(
        event_server.create_events_from_trap(_snmpv1_trap(generic_trap=0), ("192.0.2.1", 162))
    )

    assert (events, caplog.messages) == ([], [])


def test_traps_are_ignored_without_a_trap_endpoint_after_a_reload(
    event_server: EventServer,
    config: Config,
    history: FileHistory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    event_server.reload_configuration(config, history)
    caplog.set_level(logging.DEBUG, logger="cmk.mkeventd.EventServer")

    events = list(
        event_server.create_events_from_trap(_snmpv1_trap(generic_trap=0), ("192.0.2.1", 162))
    )

    assert (events, caplog.messages) == ([], [])
