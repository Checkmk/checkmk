#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import socket
from collections import namedtuple

import pytest  # type: ignore[import]

from cmk.snmplib.type_defs import SNMPTree

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


def to_json(data):
    return json.loads(json.dumps(data))


class TestIPMIDataFetcher:
    def test_deserialization(self):
        fetcher = IPMIDataFetcher.from_json(
            to_json({
                "address": "1.2.3.4",
                "username": "us3r",
                "password": "secret",
            }))
        assert isinstance(fetcher, IPMIDataFetcher)

    def test_command_raises_IpmiException_handling(self, monkeypatch):
        monkeypatch.setattr(IPMIDataFetcher, "open", lambda self: None)

        with pytest.raises(MKFetcherError):
            with IPMIDataFetcher("127.0.0.1", "", ""):
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


class TestPiggyBack:
    def test_deserialization(self):
        fetcher = PiggyBackDataFetcher.from_json(
            to_json({
                "hostname": "host",
                "address": "1.2.3.4",
                "time_settings": [],
            }))
        assert isinstance(fetcher, PiggyBackDataFetcher)


class TestProgram:
    def test_deserialization(self):
        fetcher = ProgramDataFetcher.from_json(
            to_json({
                "cmdline": "/bin/true",
                "stdin": None,
                "is_cmc": False,
            }))
        assert isinstance(fetcher, ProgramDataFetcher)


class TestSNMP:
    def test_deserialization(self):
        fetcher = SNMPDataFetcher.from_json(
            to_json({
                "oid_infos": {
                    "pim": [SNMPTree(base=".1.1.1", oids=["1.2", "3.4"]).to_json()],
                    "pam": [SNMPTree(base=".1.2.3", oids=["4.5", "6.7", "8.9"]).to_json()],
                    "pum": [
                        SNMPTree(base=".2.2.2", oids=["2.2"]).to_json(),
                        SNMPTree(base=".3.3.3", oids=["2.2"]).to_json(),
                    ],
                },
                "use_snmpwalk_cache": False,
                "snmp_config": SNMPHostConfig(
                    is_ipv6_primary=False,
                    hostname="bob",
                    ipaddress="1.2.3.4",
                    credentials=(),
                    port=42,
                    is_bulkwalk_host=False,
                    is_snmpv2or3_without_bulkwalk_host=False,
                    bulk_walk_size_of=0,
                    timing={},
                    oid_range_limits=[],
                    snmpv3_contexts=[],
                    character_encoding=None,
                    is_usewalk_host=False,
                    is_inline_snmp_host=False,
                    record_stats=False,
                )._asdict(),
            }))
        assert isinstance(fetcher, SNMPDataFetcher)


class TestTCPDataFetcher:
    def test_deserialization(self):
        fetcher = TCPDataFetcher.from_json(
            to_json({
                "family": socket.AF_INET,
                "address": "1.2.3.4",
                "timeout": 0.1,
                "encryption_settings": {
                    "encryption": "settings"
                },
            }))
        assert isinstance(fetcher, TCPDataFetcher)

    def test_decrypt_plaintext_is_noop(self):
        settings = {"use_regular": "allow"}
        output = b"<<<section:sep(0)>>>\nbody\n"
        fetcher = TCPDataFetcher(socket.AF_INET, ("", 0), 0.0, settings)

        assert fetcher._decrypt(output) == output

    def test_decrypt_plaintext_with_enforce_raises_MKFetcherError(self):
        settings = {"use_regular": "enforce"}
        output = b"<<<section:sep(0)>>>\nbody\n"
        fetcher = TCPDataFetcher(socket.AF_INET, ("", 0), 0.0, settings)

        with pytest.raises(MKFetcherError):
            fetcher._decrypt(output)

    def test_decrypt_payload_with_wrong_protocol_raises_MKFetcherError(self):
        settings = {"use_regular": "enforce"}
        output = b"the first two bytes are not a number"
        fetcher = TCPDataFetcher(socket.AF_INET, ("", 0), 0.0, settings)

        with pytest.raises(MKFetcherError):
            fetcher._decrypt(output)
