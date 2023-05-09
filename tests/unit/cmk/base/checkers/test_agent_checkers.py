#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import logging
import os
import time
from pathlib import Path

import pytest  # type: ignore[import]

from testlib.base import Scenario

from cmk.utils.exceptions import MKTimeout
from cmk.utils.type_defs import AgentRawData, result, SectionName, SourceType

from cmk.fetchers import FetcherType, MaxAge
from cmk.fetchers.agent import NoCache
from cmk.fetchers.cache import SectionStore

import cmk.base.config as config
from cmk.base.checkers import Mode
from cmk.base.checkers.agent import (
    AgentParser,
    AgentParserSectionHeader,
    AgentSectionContent,
    AgentSource,
    AgentSummarizer,
)
from cmk.base.checkers.host_sections import HostSections
from cmk.base.checkers.type_defs import NO_SELECTION
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData


class TestSummarizer:
    pass


class TestParser:
    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture
    def logger(self):
        return logging.getLogger("test")

    @pytest.fixture
    def scenario(self, hostname, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        ts.apply(monkeypatch)

    @pytest.fixture
    def patch_io(self, monkeypatch):
        monkeypatch.setattr(
            HostSections,
            "add_persisted_sections",
            lambda *args, **kwargs: None,
        )

    @pytest.fixture
    def store_path(self, tmp_path, patch_io):
        return tmp_path / "store"

    @pytest.fixture
    def store(self, store_path, logger):
        return SectionStore[AgentSectionContent](
            store_path,
            keep_outdated=False,
            logger=logger,
        )

    @pytest.fixture
    def parser(self, hostname, store, logger):
        return AgentParser(hostname, store, logger)

    @pytest.mark.usefixtures("scenario")
    def test_raw_section_populates_sections(self, parser):
        raw_data = AgentRawData(b"\n".join((
            b"<<<a_section>>>",
            b"first line",
            b"second line",
            b"<<<>>>",  # to be skipped
            b"<<<another_section>>>",
            b"first line",
            b"second line",
            b"<<<>>>",  # to be skipped
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {
            SectionName("a_section"): [["first", "line"], ["second", "line"]],
            SectionName("another_section"): [["first", "line"], ["second", "line"]],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.usefixtures("scenario")
    def test_piggyback_populates_piggyback_raw_data(self, parser, monkeypatch):
        time_time = 1000
        monkeypatch.setattr(time, "time", lambda: time_time)
        monkeypatch.setattr(config.HostConfig, "check_mk_check_interval", 10)

        raw_data = AgentRawData(b"\n".join((
            b"<<<<piggyback header>>>>",  # <- space is OK
            b"<<<section>>>",
            b"first line",
            b"second line",
            b"<<<<>>>>",  # <- omitting this line makes no difference
            b"<<<<piggyback_other>>>>",
            b"<<<other_section>>>",
            b"first line",
            b"second line",
            b"<<<<>>>>",
            b"<<<<../b:l*a../>>>>",
            b"<<<section>>>",
            b"first line",
            b"<<<</b_l-u/>>>>",
            b"<<<section>>>",
            b"first line",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggyback_header": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
                b"second line",
            ],
            "piggyback_other": [
                b"<<<other_section:cached(1000,900)>>>",
                b"first line",
                b"second line",
            ],
            ".._b_l_a.._": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
            ],
            "_b_l-u_": [
                b"<<<section:cached(1000,900)>>>",
                b"first line",
            ],
        }

    @pytest.mark.usefixtures("scenario")
    def test_persist_option_populates_cache_info_and_persisted_sections(
            self, parser, mocker, monkeypatch):
        time_time = 1000
        time_delta = 50
        monkeypatch.setattr(time, "time", lambda: time_time)
        add_persisted_sections = mocker.patch.object(
            HostSections,
            "add_persisted_sections",
        )

        raw_data = AgentRawData(b"\n".join((
            b"<<<section:persist(%i)>>>" % (time_time + time_delta),
            b"first line",
            b"second line",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {SectionName("section"): [["first", "line"], ["second", "line"]]}
        assert ahs.cache_info == {SectionName("section"): (time_time, time_delta)}
        assert ahs.piggybacked_raw_data == {}
        assert add_persisted_sections.call_args.args[0] == {
            SectionName("section"): (1000, 1050, [["first", "line"], ["second", "line"]]),
        }

    @pytest.mark.usefixtures("scenario")
    def test_section_filtering(self, parser, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: 1000)
        raw_data = AgentRawData(b"\n".join((
            b"<<<<piggyback_header>>>>",
            b"<<<deselected>>>",
            b"1st line",
            b"2nd line",
            b"<<<selected>>>",
            b"3rd line",
            b"4th line",
            b"<<<<>>>>",
            b"<<<deselected>>>",
            b"5th line",
            b"6th line",
            b"<<<selected>>>",
            b"7th line",
            b"8th line",
        )))

        ahs = parser.parse(raw_data, selection={SectionName("selected")})

        assert ahs.sections == {
            SectionName("selected"): [["7th", "line"], ["8th", "line"]],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {
            "piggyback_header": [
                b"<<<selected:cached(1000,90)>>>",
                b"3rd line",
                b"4th line",
            ]
        }

    @pytest.mark.parametrize(
        "headerline, section_name, section_options",
        [
            (b"norris", SectionName("norris"), {}),
            (b"norris:chuck", SectionName("norris"), {"chuck": None}),
            (
                b"my_section:sep(0):cached(23,42)",
                SectionName("my_section"),
                {"sep": "0", "cached": "23,42"},
            ),
            (b"my.section:sep(0):cached(23,42)", None, {}),  # invalid section name
            (b"", None, {}),  # invalid section name
        ],
    )  # yapf: disable
    def test_section_header_options(self, headerline, section_name, section_options):
        try:
            AgentParserSectionHeader.from_headerline(headerline) == (section_name, section_options)
        except ValueError:
            assert section_name is None

    def test_section_header_options_decode_values(self):
        section_header = AgentParserSectionHeader.from_headerline(b":".join((
            b"name",
            b"cached(1,2)",
            b"encoding(ascii)",
            b"nostrip()",
            b"persist(42)",
            b"sep(124)",
        )))
        assert section_header.name == SectionName("name")
        assert section_header.cached == (1, 2)
        assert section_header.encoding == "ascii"
        assert section_header.nostrip is True
        assert section_header.persist == 42
        assert section_header.separator == "|"

    def test_section_header_options_decode_nothing(self):
        section_header = AgentParserSectionHeader.from_headerline(b"name")
        assert section_header.name == SectionName("name")
        assert section_header.cached == ()
        assert section_header.encoding == "utf-8"
        assert section_header.nostrip is False
        assert section_header.persist is None
        assert section_header.separator is None


class StubSummarizer(AgentSummarizer):
    def summarize_success(self, host_sections):
        return 0, "", []


class StubSource(AgentSource):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fetcher_type=FetcherType.NONE,
            main_data_source=False,
            **kwargs,
        )

    def to_json(self):
        return {}

    def _make_file_cache(self):
        return NoCache(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=False,
            simulation=True,
        )

    def _make_fetcher(self):
        return self

    def _make_checker(self):
        return self

    def _make_summarizer(self):
        return StubSummarizer(self.exit_spec)


class TestAgentSummaryResult:
    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture(params=(mode for mode in Mode if mode is not Mode.NONE))
    def mode(self, request):
        return request.param

    @pytest.fixture
    def scenario(self, hostname, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        ts.apply(monkeypatch)
        return ts

    @pytest.fixture
    def source(self, hostname, mode):
        return StubSource(
            hostname,
            "1.2.3.4",
            mode=mode,
            source_type=SourceType.HOST,
            id_="agent_id",
            description="agent description",
        )

    @pytest.mark.usefixtures("scenario")
    def test_defaults(self, source):
        assert source.summarize(result.OK(source.default_host_sections)) == (0, "", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_exception(self, source):
        assert source.summarize(result.Error(Exception())) == (3, "(?)", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_MKEmptyAgentData_exception(self, source):
        assert source.summarize(result.Error(MKEmptyAgentData())) == (2, "(!!)", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_MKAgentError_exception(self, source):
        assert source.summarize(result.Error(MKAgentError())) == (2, "(!!)", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_MKTimeout_exception(self, source):
        assert source.summarize(result.Error(MKTimeout())) == (2, "(!!)", [])
