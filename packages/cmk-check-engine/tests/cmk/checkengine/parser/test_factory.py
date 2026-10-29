#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.helper_interface import AgentRawData, FetcherType
from cmk.checkengine.parser import (
    AgentRawDataSection,
    make_parser,
    NO_SELECTION,
    Parser,
    ParserConfig,
)
from cmk.checkengine.plugins import SectionName


def _make_agent_parser(
    fetcher_type: FetcherType, cached_at: int | None, tmp_path: Path
) -> Parser[AgentRawData, AgentRawDataSection]:
    return make_parser(
        ParserConfig(
            fallback_agent_output_encoding="ascii",
            check_interval=lambda _host_name: 60.0,
            piggyback_translations=lambda _host_name: {},
            piggyback_max_cache_age_callbacks=lambda _host_name: lambda _source: 0,
        ),
        HostName("testhost"),
        None,
        fetcher_type,
        cached_at=cached_at,
        omd_root=tmp_path,
        persisted_section_dir=tmp_path / "persisted",
        keep_outdated=False,
        debug=False,
    )


def test_push_agent_sections_are_cached_since_arrival_for_the_push_interval(
    tmp_path: Path,
) -> None:
    parser = _make_agent_parser(FetcherType.PUSH_AGENT, 1000, tmp_path)

    host_sections = parser.parse(AgentRawData(b"<<<kernel>>>\nline"), selection=NO_SELECTION)

    assert host_sections.cache_info == {SectionName("kernel"): (1000, 60)}


def test_push_agent_sections_keep_their_own_cache_info(tmp_path: Path) -> None:
    parser = _make_agent_parser(FetcherType.PUSH_AGENT, 1000, tmp_path)

    host_sections = parser.parse(
        AgentRawData(b"<<<logwatch:cached(900,300)>>>\nline"), selection=NO_SELECTION
    )

    assert host_sections.cache_info == {SectionName("logwatch"): (900, 300)}


def test_pulled_agent_sections_are_not_cached(tmp_path: Path) -> None:
    parser = _make_agent_parser(FetcherType.TCP, 1000, tmp_path)

    host_sections = parser.parse(AgentRawData(b"<<<kernel>>>\nline"), selection=NO_SELECTION)

    assert not host_sections.cache_info
