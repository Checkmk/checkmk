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
from cmk.utils.type_defs import ErrorResult, OKResult, SectionName, SourceType

from cmk.fetchers import FetcherType
from cmk.fetchers.agent import NoCache

import cmk.base.config as config
from cmk.base.checkers import Mode
from cmk.base.checkers.agent import AgentParser, AgentSource, AgentSummarizer
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

    @pytest.mark.usefixtures("scenario")
    def test_raw_section_populates_sections(self, hostname, logger):
        raw_data = b"\n".join((
            b"<<<a_section>>>",
            b"first line",
            b"second line",
            b"<<<another_section>>>",
            b"first line",
            b"second line",
        ))

        ahs = AgentParser(hostname, Path(""), logger).parse(OKResult(raw_data)).ok

        assert ahs.sections == {
            SectionName("a_section"): [["first", "line"], ["second", "line"]],
            SectionName("another_section"): [["first", "line"], ["second", "line"]],
        }
        assert ahs.cache_info == {}
        assert ahs.piggybacked_raw_data == {}
        assert ahs.persisted_sections == {}

    @pytest.mark.usefixtures("scenario")
    def test_piggyback_populates_piggyback_raw_data(self, hostname, logger, monkeypatch):
        time_time = 1000
        monkeypatch.setattr(time, "time", lambda: time_time)
        monkeypatch.setattr(config.HostConfig, "check_mk_check_interval", 10)

        raw_data = b"\n".join((
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
        ))

        ahs = AgentParser(hostname, Path(""), logger).parse(OKResult(raw_data)).ok

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
        assert ahs.persisted_sections == {}

    @pytest.mark.usefixtures("scenario")
    def test_persist_option_populates_cache_info_and_persisted_sections(
        self,
        hostname,
        logger,
        monkeypatch,
    ):
        time_time = 1000
        time_delta = 50
        monkeypatch.setattr(time, "time", lambda: time_time)

        raw_data = b"\n".join((
            b"<<<section:persist(%i)>>>" % (time_time + time_delta),
            b"first line",
            b"second line",
        ))

        ahs = AgentParser(hostname, Path(""), logger).parse(OKResult(raw_data)).ok

        assert ahs.sections == {SectionName("section"): [["first", "line"], ["second", "line"]]}
        assert ahs.cache_info == {SectionName("section"): (time_time, time_delta)}
        assert ahs.piggybacked_raw_data == {}
        assert ahs.persisted_sections == {
            SectionName("section"): (1000, 1050, [["first", "line"], ["second", "line"]]),
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
        ],
    )  # yapf: disable
    def test_section_header_options(self, headerline, section_name, section_options):
        parsed_name, parsed_options = AgentParser._parse_section_header(headerline)
        assert parsed_name == section_name
        assert parsed_options == section_options


class StubSummarizer(AgentSummarizer):
    def _summarize(self, host_sections):
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
            cpu_tracking_id="agent_cpu_id",
            description="agent description",
        )

    @pytest.mark.usefixtures("scenario")
    def test_defaults(self, source):
        assert source.summarize(OKResult(source.default_host_sections)) == (0, "", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_exception(self, source):
        assert source.summarize(ErrorResult(Exception())) == (3, "(?)", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_MKEmptyAgentData_exception(self, source):
        assert source.summarize(ErrorResult(MKEmptyAgentData())) == (2, "(!!)", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_MKAgentError_exception(self, source):
        assert source.summarize(ErrorResult(MKAgentError())) == (2, "(!!)", [])

    @pytest.mark.usefixtures("scenario")
    def test_with_MKTimeout_exception(self, source):
        assert source.summarize(ErrorResult(MKTimeout())) == (2, "(!!)", [])
