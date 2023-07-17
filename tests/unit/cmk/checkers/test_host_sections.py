#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypeAlias

import cmk.utils.resulttype as result
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.sectionname import SectionName

from cmk.fetchers import FetcherType

from cmk.checkengine import HostKey, HostSections, SourceInfo, SourceType
from cmk.checkengine.sectionparser import filter_out_errors
from cmk.checkengine.type_defs import AgentRawDataSection

HS: TypeAlias = HostSections[AgentRawDataSection]
TRAW: TypeAlias = list[tuple[str, str]]


def make_source_info(
    host_name: HostName | None = None,
    host_addr: HostAddress | None = None,
    ident: str | None = None,
    fetcher_type: FetcherType | None = None,
    source_type: SourceType | None = None,
) -> SourceInfo:
    """Provide usable defaults."""
    return SourceInfo(
        host_name or HostName("testhost"),
        host_addr or HostAddress("192.0.2.4"),
        ident or "ident",
        fetcher_type or FetcherType.TCP,
        source_type or SourceType.HOST,
    )


def make_host_key(source_info: SourceInfo) -> HostKey:
    return HostKey(source_info.hostname, source_info.source_type)


def parse(raw: TRAW) -> dict[SectionName, list[list[str]]]:
    return {SectionName(name): [line.split() for line in lines.splitlines()] for name, lines in raw}


class TestFilterOutErrors:
    def test_nothing_noop(self):
        RAW: TRAW = []

        host_sections = HS(parse(RAW))
        source_info = make_source_info()

        assert filter_out_errors([(source_info, result.OK(host_sections))]) == {
            make_host_key(source_info): HS({})
        }

    def test_sections_noop(self):
        RAW = [
            ("section0", "first line\nsectond line"),
            ("section1", "third line\nforth line"),
        ]

        host_sections = HS(parse(RAW))
        source_info = make_source_info()

        assert filter_out_errors([(source_info, result.OK(host_sections))]) == {
            make_host_key(source_info): HS(parse(RAW))
        }

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
        source_info = make_source_info()

        assert filter_out_errors(
            [
                (source_info, result.OK(host_sections_1)),
                (source_info, result.OK(host_sections_2)),
            ]
        ) == {make_host_key(source_info): HS(parse(RAW_1 + RAW_2))}
        # check for input mutation
        assert host_sections_1 == HS(parse(RAW_1))
        assert host_sections_2 == HS(parse(RAW_2))

    def test_piggybacked_raw_noop(self):
        RAW: TRAW = []
        PB = {HostName("piggybacked"): [b"aaa", b"bbb", b"ccc"]}

        host_sections = HS(parse(RAW), piggybacked_raw_data=PB)
        source_info = make_source_info()

        assert filter_out_errors([(source_info, result.OK(host_sections))]) == {
            make_host_key(source_info): HS(parse(RAW), piggybacked_raw_data=PB)
        }

    def test_piggybacked_raw_merge_sources(self):
        host_name = HostName("piggybacked")
        RAW_1: TRAW = []
        PB_1 = [b"aaa", b"bbb", b"ccc"]

        RAW_2: TRAW = []
        PB_2 = [b"ddd", b"eee", b"fff"]

        host_sections_1 = HS(parse(RAW_1), piggybacked_raw_data={host_name: PB_1})
        host_sections_2 = HS(parse(RAW_2), piggybacked_raw_data={host_name: PB_2})
        source_info = make_source_info()

        assert filter_out_errors(
            [
                (source_info, result.OK(host_sections_1)),
                (source_info, result.OK(host_sections_2)),
            ]
        ) == {
            make_host_key(source_info): HS(
                parse(RAW_1 + RAW_2), piggybacked_raw_data={host_name: PB_1 + PB_2}
            )
        }

    def test_cache_info_noop(self):
        RAW: TRAW = []
        CACHE_INFO = {SectionName("aaa"): (1, 2)}

        host_section = HS(parse(RAW), cache_info=CACHE_INFO)
        source_info = make_source_info()

        assert filter_out_errors([(source_info, result.OK(host_section))]) == {
            make_host_key(source_info): HS(parse(RAW), cache_info=CACHE_INFO)
        }

    def test_cache_info_last_overwrites_previous_values(self):
        section = SectionName("aaa")
        RAW_1: TRAW = []
        CACHE_INFO_1 = {section: (1, 2)}

        RAW_2: TRAW = []
        CACHE_INFO_2 = {section: (3, 4)}

        host_sections_1 = HS(parse(RAW_1), cache_info=CACHE_INFO_1)
        host_sections_2 = HS(parse(RAW_2), cache_info=CACHE_INFO_2)
        source_info = make_source_info()

        assert filter_out_errors(
            [
                (source_info, result.OK(host_sections_1)),
                (source_info, result.OK(host_sections_2)),
            ]
        ) == {make_host_key(source_info): HS(parse(RAW_1 + RAW_2), cache_info=CACHE_INFO_2)}
