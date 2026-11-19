#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Translating the var binds of SNMP traps"""

import logging

import pytest
from pysnmp.proto.rfc1902 import ObjectName, OctetString

import cmk.ec.export as ec
from cmk.ec.config import Config
from cmk.ec.snmp import SNMPTrapTranslator

# sysORDescr.1.2, but sysORTable has only one index.
UNTRANSLATABLE_OID = ObjectName("1.3.6.1.2.1.1.9.1.3.1.2")


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
