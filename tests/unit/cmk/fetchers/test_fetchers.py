#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import socket
from collections import namedtuple

import pytest  # type: ignore[import]

from cmk.snmplib.type_defs import SNMPHostConfig, SNMPTree

from cmk.fetchers import AgentFileCache, FetcherType, MKFetcherError, SNMPFileCache
from cmk.fetchers.ipmi import IpmiException, IPMIFetcher
from cmk.fetchers.piggyback import PiggyBackFetcher
from cmk.fetchers.program import ProgramFetcher
from cmk.fetchers.snmp import SNMPFetcher
from cmk.fetchers.tcp import TCPFetcher

from cmk.base.data_sources import FileCacheConfigurator

SensorReading = namedtuple(
    "SensorReading", "states health name imprecision units"
    " state_ids type value unavailable")


def json_identity(data):
    return json.loads(json.dumps(data))


@pytest.fixture(name="fc_conf")
def fc_conf_fixture():
    return FileCacheConfigurator("/dev/null", FetcherType.NONE)


@pytest.fixture(name="fc_agent")
def fc_agent_fixture(fc_conf):
    return AgentFileCache.from_json(fc_conf.configure())


@pytest.fixture(name="fc_snmp")
def fc_snmp_fixture(fc_conf):
    return SNMPFileCache.from_json(fc_conf.configure())


class TestIPMIFetcher:
    def test_deserialization(self, fc_conf):
        fetcher = IPMIFetcher.from_json(
            json_identity({
                "file_cache": fc_conf.configure(),
                "address": "1.2.3.4",
                "username": "us3r",
                "password": "secret",
            }))
        assert isinstance(fetcher, IPMIFetcher)

    def test_command_raises_IpmiException_handling(self, fc_agent, monkeypatch):
        monkeypatch.setattr(IPMIFetcher, "open", lambda self: None)

        with pytest.raises(MKFetcherError):
            with IPMIFetcher(fc_agent, "127.0.0.1", "", ""):
                raise IpmiException()

    def test_parse_sensor_reading_standard_case(self):
        reading = SensorReading(  #
            ['lower non-critical threshold'], 1, "Hugo", None, "", [42], "hugo-type", None, 0)
        assert IPMIFetcher._parse_sensor_reading(  #
            0, reading) == [b"0", b"Hugo", b"hugo-type", b"N/A", b"", b"WARNING"]

    def test_parse_sensor_reading_false_positive(self):
        reading = SensorReading(  #
            ['Present'], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice", 3.14159265, 1)
        assert IPMIFetcher._parse_sensor_reading(  #
            0, reading) == [b"0", b"Dingeling", b"FancyDevice", b"3.14", b"C", b"Present"]


class TestPiggyBack:
    def test_deserialization(self, fc_conf):
        fetcher = PiggyBackFetcher.from_json(
            json_identity({
                "file_cache": fc_conf.configure(),
                "hostname": "host",
                "address": "1.2.3.4",
                "time_settings": [],
            }))
        assert isinstance(fetcher, PiggyBackFetcher)


class TestProgram:
    def test_deserialization(self, fc_conf):
        fetcher = ProgramFetcher.from_json(
            json_identity({
                "file_cache": fc_conf.configure(),
                "cmdline": "/bin/true",
                "stdin": None,
                "is_cmc": False,
            }))
        assert isinstance(fetcher, ProgramFetcher)


class TestSNMP:
    def test_deserialization(self, fc_conf):
        fetcher = SNMPFetcher.from_json(
            json_identity({
                "file_cache": fc_conf.configure(),
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
        assert isinstance(fetcher, SNMPFetcher)


class TestTCPFetcher:
    def test_deserialization(self, fc_conf):
        fetcher = TCPFetcher.from_json(
            json_identity({
                "file_cache": fc_conf.configure(),
                "family": socket.AF_INET,
                "address": "1.2.3.4",
                "timeout": 0.1,
                "encryption_settings": {
                    "encryption": "settings"
                },
            }))
        assert isinstance(fetcher, TCPFetcher)

    def test_decrypt_plaintext_is_noop(self, fc_agent):
        settings = {"use_regular": "allow"}
        output = b"<<<section:sep(0)>>>\nbody\n"
        fetcher = TCPFetcher(fc_agent, socket.AF_INET, ("", 0), 0.0, settings)

        assert fetcher._decrypt(output) == output

    def test_decrypt_plaintext_with_enforce_raises_MKFetcherError(self, fc_agent):
        settings = {"use_regular": "enforce"}
        output = b"<<<section:sep(0)>>>\nbody\n"
        fetcher = TCPFetcher(fc_agent, socket.AF_INET, ("", 0), 0.0, settings)

        with pytest.raises(MKFetcherError):
            fetcher._decrypt(output)

    def test_decrypt_payload_with_wrong_protocol_raises_MKFetcherError(self, fc_agent):
        settings = {"use_regular": "enforce"}
        output = b"the first two bytes are not a number"
        fetcher = TCPFetcher(fc_agent, socket.AF_INET, ("", 0), 0.0, settings)

        with pytest.raises(MKFetcherError):
            fetcher._decrypt(output)
