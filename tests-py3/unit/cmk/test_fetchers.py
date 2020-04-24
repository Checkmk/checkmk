#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import namedtuple

import pytest  # type: ignore[import]

# pylint: disable=wildcard-import,unused-wildcard-import
from cmk.fetchers.ipmi import *
from cmk.fetchers.piggyback import *
from cmk.fetchers.program import *
from cmk.fetchers.snmp import *
from cmk.fetchers.tcp import *
# pylint: enable=wildcard-import,unused-wildcard-import

SensorReading = namedtuple(
    "SensorReading", "states health name imprecision units"
    " state_ids type value unavailable")


class TestIPMIDataFetcher:
    def test_command_raises_IpmiException_handling(self, monkeypatch):
        monkeypatch.setattr(IPMIDataFetcher, "open", lambda self: None)

        with pytest.raises(MKAgentError):
            with IPMIDataFetcher("127.0.0.1", "", "", logging.getLogger("tests")):
                raise IpmiException()

    def test_parse_sensor_reading_standard_case(self):
        reading = SensorReading(  #
            ['lower non-critical threshold'], 1, "Hugo", None, "", [42], "hugo-type", None, 0)
        assert IPMIDataFetcher._parse_sensor_reading(  #
            0, reading) == [b"0", b"Hugo", b"hugo-type", b"N/A", b"", b"WARNING"]

    def test_parse_sensor_reading_false_positive(self):
        reading = SensorReading(  #
            ['Present'], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice", 3.14159265, 1)
        assert IPMIDataFetcher._parse_sensor_reading(  #
            0, reading) == [b"0", b"Dingeling", b"FancyDevice", b"3.14", b"C", b"Present"]


class TestTCPDataFetcher:
    def test_decrypt_plaintext_is_noop(self):
        settings = {"use_regular": "allow"}
        output = b"<<<section:sep(0)>>>\nbody\n"
        fetcher = TCPDataFetcher(socket.AF_INET, ("", 0), 0.0, settings, logging.getLogger("test"))

        assert fetcher._decrypt(output) == output

    def test_decrypt_plaintext_with_enforce_raises_MKAgentError(self):
        settings = {"use_regular": "enforce"}
        output = b"<<<section:sep(0)>>>\nbody\n"
        fetcher = TCPDataFetcher(socket.AF_INET, ("", 0), 0.0, settings, logging.getLogger("test"))

        with pytest.raises(MKAgentError):
            fetcher._decrypt(output)

    def test_decrypt_payload_with_wrong_protocol_raises_MKAgentError(self):
        settings = {"use_regular": "enforce"}
        output = b"the first two bytes are not a number"
        fetcher = TCPDataFetcher(socket.AF_INET, ("", 0), 0.0, settings, logging.getLogger("test"))

        with pytest.raises(MKAgentError):
            fetcher._decrypt(output)
