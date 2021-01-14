#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest  # type: ignore[import]

from cmk.utils.exceptions import MKAgentError, MKEmptyAgentData, MKTimeout
from cmk.utils.type_defs import ExitSpec, AgentRawData

from cmk.core_helpers.type_defs import Mode
from cmk.core_helpers.agent import AgentSummarizer


class Summarizer(AgentSummarizer):
    def summarize_success(self, host_sections, *, mode):
        return 0, "", []


class TestAgentSummarizer:
    @pytest.fixture
    def summarizer(self):
        return Summarizer(ExitSpec())

    @pytest.fixture(params=Mode)
    def mode(self, request):
        return request.param

    def test_summarize_success(self, summarizer, mode):
        assert summarizer.summarize_success(AgentRawData(b""), mode=mode) == (0, "", [])

    def test_summarize_base_exception(self, summarizer, mode):
        assert summarizer.summarize_failure(Exception(), mode=mode) == (3, "(?)", [])

    def test_summarize_MKEmptyAgentData_exception(self, summarizer, mode):
        assert summarizer.summarize_failure(MKEmptyAgentData(), mode=mode) == (2, "(!!)", [])

    def test_summarize_MKAgentError_exception(self, summarizer, mode):
        assert summarizer.summarize_failure(MKAgentError(), mode=mode) == (2, "(!!)", [])

    def test_summarize_MKTimeout_exception(self, summarizer, mode):
        assert summarizer.summarize_failure(MKTimeout(), mode=mode) == (2, "(!!)", [])
