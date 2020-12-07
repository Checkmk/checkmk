#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
from cmk.utils.type_defs import AgentRawData, AgentRawDataSection, result, SectionName, SourceType

from cmk.fetchers import FetcherType
from cmk.fetchers.agent import NoCache
from cmk.fetchers.cache import PersistedSections, SectionStore

from cmk.base.checkers import Mode
from cmk.base.checkers.agent import AgentParser, AgentSource, AgentSummarizer, HostSectionParser
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
    def store_path(self, tmp_path):
        return tmp_path / "store"

    @pytest.fixture
    def store(self, store_path, logger):
        return SectionStore[AgentRawDataSection](
            store_path,
            keep_outdated=False,
            logger=logger,
        )

    @pytest.fixture
    def parser(self, hostname, store, logger):
        return AgentParser(hostname, store, 0, logger)

    @pytest.mark.usefixtures("scenario")
    def test_missing_host_header(self, parser):
        raw_data = AgentRawData(b"\n".join((
            b"hey!",
            b"a header",
            b"is missing",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.usefixtures("scenario")
    def test_piggy_name_as_hostname_is_not_piggybacked(self, parser, hostname):
        raw_data = AgentRawData(b"\n".join((
            f"<<<<{hostname}>>>>".encode("ascii"),
            b"line0",
            b"line1",
            b"line2",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.usefixtures("scenario")
    def test_no_host_header_after_piggyback(self, parser):
        raw_data = AgentRawData(b"\n".join((
            b"<<<<piggy>>>>",
            b"line0",
            b"line1",
            b"line2",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)
        assert ahs.sections == {}
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {'piggy': [b"line0", b"line1", b"line2"]}

    @pytest.mark.usefixtures("scenario")
    def test_raw_section_populates_sections(self, parser):
        raw_data = AgentRawData(b"\n".join((
            b"<<<a_section>>>",
            b"first line",
            b"second line",
            b"<<<>>>",
            b"<<<another_section>>>",
            b"first line",
            b"second line",
            b"<<<>>>",
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
        monkeypatch.setattr(parser, "check_interval", 10)

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
            b"<<<other_other_section>>>",
            b"third line",
            b"forth line",
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
                b"<<<other_other_section:cached(1000,900)>>>",
                b"third line",
                b"forth line",
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
    def test_persist_option_populates_cache_info(self, parser, mocker, monkeypatch):
        time_time = 1000
        time_delta = 50
        monkeypatch.setattr(time, "time", lambda: time_time)

        raw_data = AgentRawData(b"\n".join((
            b"<<<section:persist(%i)>>>" % (time_time + time_delta),
            b"first line",
            b"second line",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {SectionName("section"): [["first", "line"], ["second", "line"]]}
        assert ahs.cache_info == {SectionName("section"): (time_time, time_delta)}
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.usefixtures("scenario")
    def test_persist_option_and_persisted_sections(self, parser, mocker, monkeypatch):
        time_time = 1000
        time_delta = 50
        monkeypatch.setattr(time, "time", lambda: time_time)
        monkeypatch.setattr(
            SectionStore,
            "load",
            lambda self: PersistedSections({
                SectionName("persisted"): (42, 69, [["content"]]),
            }),
        )
        # Patch IO:
        monkeypatch.setattr(SectionStore, "store", lambda self, sections: None)

        raw_data = AgentRawData(b"\n".join((
            b"<<<section:persist(%i)>>>" % (time_time + time_delta),
            b"first line",
            b"second line",
        )))

        ahs = parser.parse(raw_data, selection=NO_SELECTION)

        assert ahs.sections == {
            SectionName("section"): [["first", "line"], ["second", "line"]],
            SectionName("persisted"): [["content"]],
        }
        assert ahs.cache_info == {
            SectionName("section"): (time_time, time_delta),
            SectionName("persisted"): (42, 27),
        }
        assert ahs.piggybacked_raw_data == {}

    @pytest.mark.parametrize(
        "headerline, section_name, section_options",
        [
            ("norris", SectionName("norris"), {}),
            ("norris:chuck", SectionName("norris"), {"chuck": None}),
            (
                "my_section:sep(0):cached(23,42)",
                SectionName("my_section"),
                {"sep": "0", "cached": "23,42"},
            ),
            ("my.section:sep(0):cached(23,42)", None, {}),  # invalid section name
            ("", None, {}),  # invalid section name
        ],
    )  # yapf: disable
    def test_section_header_options(self, headerline, section_name, section_options):
        try:
            HostSectionParser.Header.from_headerline(
                f"<<<{headerline}>>>".encode("ascii")) == (  # type: ignore[comparison-overlap]
                    section_name,
                    section_options,
                )
        except ValueError:
            assert section_name is None

    def test_section_header_options_decode_values(self):
        section_header = HostSectionParser.Header.from_headerline(b"<<<" + b":".join((
            b"name",
            b"cached(1,2)",
            b"encoding(ascii)",
            b"nostrip()",
            b"persist(42)",
            b"sep(124)",
        )) + b">>>")
        assert section_header.name == SectionName("name")
        assert section_header.cached == (1, 2)
        assert section_header.encoding == "ascii"
        assert section_header.nostrip is True
        assert section_header.persist == 42
        assert section_header.separator == "|"

    def test_section_header_options_decode_nothing(self):
        section_header = HostSectionParser.Header.from_headerline(b"<<<name>>>")
        assert section_header.name == SectionName("name")
        assert section_header.cached is None
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
            path=Path(os.devnull),
            max_age=0,
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
