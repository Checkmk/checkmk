#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypeAlias

from cmk.ccc.hostaddress import HostName

from cmk.utils.sectionname import SectionName

from cmk.checkengine.fetcher import HostKey, SourceType
from cmk.checkengine.parser import AgentRawDataSection, group_by_host, HostSections

HS: TypeAlias = HostSections[AgentRawDataSection]
TRAW: TypeAlias = list[tuple[str, str]]


def parse(raw: TRAW) -> dict[SectionName, list[list[str]]]:
    return {SectionName(name): [line.split() for line in lines.splitlines()] for name, lines in raw}


def _log(message: str) -> None:
    pass


class TestGroupByHost:
    def test_nothing_noop(self):
        RAW: TRAW = []

        host_sections = HS(parse(RAW))
        host_key = HostKey(HostName("testhost"), SourceType.HOST)

        assert group_by_host([(host_key, host_sections)], _log) == {host_key: HS({})}

    def test_sections_noop(self):
        RAW = [
            ("section0", "first line\nsectond line"),
            ("section1", "third line\nforth line"),
        ]

        host_sections = HS(parse(RAW))
        host_key = HostKey(HostName("testhost"), SourceType.HOST)

        assert group_by_host([(host_key, host_sections)], _log) == {host_key: HS(parse(RAW))}

    def test_sections_merge_sources(self):
        RAW_1 = [
            ("section0", "first line\nsectond line"),
            ("section1", "third line\nforth line"),
        ]
        RAW_2 = [
            ("section2", "fifth line\nsixth line"),
            ("section3", "seventh line\neigth line"),
        ]

        host_sections_1 = HS(parse(RAW_1))
        host_sections_2 = HS(parse(RAW_2))
        host_key = HostKey(HostName("testhost"), SourceType.HOST)

        assert group_by_host([(host_key, host_sections_1), (host_key, host_sections_2)], _log) == {
            host_key: HS(parse(RAW_1 + RAW_2))
        }
        # check for input mutation
        assert host_sections_1 == HS(parse(RAW_1))
        assert host_sections_2 == HS(parse(RAW_2))

    def test_piggybacked_raw_noop(self):
        RAW: TRAW = []
        PB = {HostName("piggybacked"): [b"aaa", b"bbb", b"ccc"]}

        host_sections = HS(parse(RAW), piggybacked_raw_data=PB)
        host_key = HostKey(HostName("testhost"), SourceType.HOST)

        assert group_by_host([(host_key, host_sections)], _log) == {
            host_key: HS(parse(RAW), piggybacked_raw_data=PB)
        }

    def test_piggybacked_raw_merge_sources(self):
        host_name = HostName("piggybacked")
        RAW_1: TRAW = []
        PB_1 = [b"aaa", b"bbb", b"ccc"]

        RAW_2: TRAW = []
        PB_2 = [b"ddd", b"eee", b"fff"]

        host_sections_1 = HS(parse(RAW_1), piggybacked_raw_data={host_name: PB_1})
        host_sections_2 = HS(parse(RAW_2), piggybacked_raw_data={host_name: PB_2})
        host_key = HostKey(HostName("testhost"), SourceType.HOST)

        assert group_by_host([(host_key, host_sections_1), (host_key, host_sections_2)], _log) == {
            host_key: HS(parse(RAW_1 + RAW_2), piggybacked_raw_data={host_name: PB_1 + PB_2})
        }

    def test_cache_info_noop(self):
        RAW: TRAW = []
        CACHE_INFO = {SectionName("aaa"): (1, 2)}

        host_section = HS(parse(RAW), cache_info=CACHE_INFO)
        host_key = HostKey(HostName("testhost"), SourceType.HOST)

        assert group_by_host([(host_key, host_section)], _log) == {
            host_key: HS(parse(RAW), cache_info=CACHE_INFO)
        }

    def test_cache_info_last_overwrites_previous_values(self):
        section = SectionName("aaa")
        RAW_1: TRAW = []
        CACHE_INFO_1 = {section: (1, 2)}

        RAW_2: TRAW = []
        CACHE_INFO_2 = {section: (3, 4)}

        host_sections_1 = HS(parse(RAW_1), cache_info=CACHE_INFO_1)
        host_sections_2 = HS(parse(RAW_2), cache_info=CACHE_INFO_2)
        host_key = HostKey(HostName("testhost"), SourceType.HOST)

        assert group_by_host([(host_key, host_sections_1), (host_key, host_sections_2)], _log) == {
            host_key: HS(parse(RAW_1 + RAW_2), cache_info=CACHE_INFO_2)
        }
