#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import os
from pathlib import Path

import pytest  # type: ignore[import]

from testlib.base import Scenario

from cmk.utils.exceptions import MKAgentError, MKEmptyAgentData, MKTimeout
from cmk.utils.type_defs import result, SourceType

from cmk.core_helpers import FetcherType
from cmk.core_helpers.type_defs import Mode
from cmk.core_helpers.agent import AgentSummarizer, NoCache

from cmk.base.sources.agent import AgentSource


class StubSummarizer(AgentSummarizer):
    def summarize_success(self, host_sections, *, mode):
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
