#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import logging
import time

import pytest  # type: ignore[import]

from testlib.base import Scenario

from cmk.utils.type_defs import SectionName

import cmk.base.data_sources.agent as agent


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

    def test_raw_section_populates_sections(self, hostname, logger):
        raw_data = b"\n".join((
            b"<<<a_section>>>",
            b"first line",
            b"second line",
            b"<<<another_section>>>",
            b"first line",
            b"second line",
        ))

        ahs = agent.Parser(logger).parse(hostname, raw_data, check_interval=10)

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

        raw_data = b"\n".join((
            b"<<<<piggyback header>>>>",  # <- space is OK
            b"<<<section>>>",
            b"first line",
            b"second line",
            b"<<<<>>>>",  #  <- omitting this line makes no difference
            b"<<<<piggyback_other>>>>",
            b"<<<other_section>>>",
            b"first line",
            b"second line",
            b"<<<<>>>>",
        ))

        ahs = agent.Parser(logger).parse(hostname, raw_data, check_interval=10)

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
        }
        assert ahs.persisted_sections == {}

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

        ahs = agent.Parser(logger).parse(hostname, raw_data, check_interval=10)
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
        parsed_name, parsed_options = agent.Parser._parse_section_header(headerline)
        assert parsed_name == section_name
        assert parsed_options == section_options
