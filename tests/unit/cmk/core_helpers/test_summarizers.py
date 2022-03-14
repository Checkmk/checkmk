#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# pylint: disable=undefined-variable
import json
from typing import Final

import pytest

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import MKAgentError, MKEmptyAgentData, MKTimeout
from cmk.utils.piggyback import PiggybackRawDataInfo
from cmk.utils.type_defs import AgentRawData, ExitSpec, HostName

import cmk.core_helpers.piggyback
from cmk.core_helpers.agent import AgentRawDataSection, AgentSummarizer, AgentSummarizerDefault
from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.piggyback import PiggybackSummarizer
from cmk.core_helpers.type_defs import Mode

CONTROLLER_STATUS_LEGACY: Final = json.dumps(
    {
        "allow_legacy_pull": True,
        "connections": [],
    }
).split()

CONTROLLER_STATUS_REGISTERED: Final = json.dumps(
    {
        "allow_legacy_pull": False,
        "connections": [
            {"connection": "localhost:8000/heute"},  # shortened for readability
        ],
    }
).split()


class Summarizer(AgentSummarizer):
    def summarize_success(self, host_sections, *, mode):
        return [ActiveCheckResult()]


class TestAgentSummarizer:
    @pytest.fixture
    def summarizer(self):
        return Summarizer(ExitSpec())

    @pytest.fixture(params=Mode)
    def mode(self, request):
        return request.param

    def test_summarize_success(self, summarizer, mode):
        assert summarizer.summarize_success(AgentRawData(b""), mode=mode) == [ActiveCheckResult(0)]

    def test_summarize_base_exception(self, summarizer, mode):
        assert summarizer.summarize_failure(Exception(), mode=mode) == [ActiveCheckResult(3)]

    def test_summarize_MKEmptyAgentData_exception(self, summarizer, mode):
        assert summarizer.summarize_failure(MKEmptyAgentData(), mode=mode) == [ActiveCheckResult(2)]

    def test_summarize_MKAgentError_exception(self, summarizer, mode):
        assert summarizer.summarize_failure(MKAgentError(), mode=mode) == [ActiveCheckResult(2)]

    def test_summarize_MKTimeout_exception(self, summarizer, mode):
        assert summarizer.summarize_failure(MKTimeout(), mode=mode) == [ActiveCheckResult(2)]


class TestAgentSummarizerDefault_AllModes:
    @pytest.fixture
    def summarizer(self):
        return AgentSummarizerDefault(ExitSpec())

    @pytest.fixture(params=Mode)
    def mode(self, request):
        return request.param

    def test_missing_section(self, summarizer, mode):
        assert summarizer.summarize_success(None, mode=mode) == [ActiveCheckResult(0, "Success")]

    def test_random_section(self, summarizer, mode):
        assert summarizer.summarize_success(
            [["some_random", "data"], ["that_does", "nothing"]],
            mode=mode,
        ) == [ActiveCheckResult(0, "Success")]


class TestPiggybackSummarizer:
    @pytest.fixture(params=["testhost", None])
    def hostname(self, request):
        return request.param

    @pytest.fixture(params=["1.2.3.4", None])
    def ipaddress(self, request):
        return request.param

    @pytest.fixture
    def summarizer(self, hostname, ipaddress):
        return PiggybackSummarizer(
            {},
            hostname=hostname,
            ipaddress=ipaddress,
            time_settings=[("", "", 0)],
            always=False,
        )

    @pytest.fixture
    def host_sections(self):
        return HostSections[AgentRawDataSection](
            sections={},
            cache_info={},
            piggybacked_raw_data={HostName("other"): [b"line0", b"line1"]},
        )

    @pytest.fixture
    def patch_get_piggyback_raw_data(self, monkeypatch):
        monkeypatch.setattr(
            cmk.core_helpers.piggyback,
            "get_piggyback_raw_data",
            lambda *args, **kwargs: (),
        )

    def test_repr_smoke_test(self, summarizer):
        assert isinstance(repr(summarizer), str)

    @pytest.mark.usefixtures("patch_get_piggyback_raw_data")
    def test_discovery_is_noop(self, summarizer, host_sections):
        assert not summarizer.summarize_success(
            host_sections,
            mode=Mode.DISCOVERY,
        )

    @pytest.mark.usefixtures("patch_get_piggyback_raw_data")
    def test_summarize_missing_data(self, summarizer, host_sections):
        assert not summarizer.summarize_success(
            host_sections,
            mode=Mode.CHECKING,
        )

    @pytest.mark.usefixtures("patch_get_piggyback_raw_data")
    def test_summarize_missing_data_with_always_option(
        self,
        summarizer,
        host_sections,
        monkeypatch,
    ):
        monkeypatch.setattr(summarizer, "always", True)

        assert summarizer.summarize_success(
            host_sections,
            mode=Mode.CHECKING,
        ) == [ActiveCheckResult(1, "Missing data")]

    def test_summarize_existing_data_with_always_option(
        self,
        summarizer,
        host_sections,
        monkeypatch,
    ):
        def get_piggyback_raw_data(source_hostname, time_settings):
            if not source_hostname:
                return ()
            return [
                PiggybackRawDataInfo(
                    source_hostname=source_hostname,
                    file_path="/dev/null",
                    successfully_processed=True,
                    reason="success",
                    reason_status=0,
                    raw_data=AgentRawData(b""),
                )
            ]

        monkeypatch.setattr(summarizer, "always", True)
        monkeypatch.setattr(
            cmk.core_helpers.piggyback,
            "get_piggyback_raw_data",
            get_piggyback_raw_data,
        )

        if summarizer.hostname is None and summarizer.ipaddress is None:
            return pytest.skip()

        assert all(
            r == ActiveCheckResult(0, "success")
            for r in summarizer.summarize_success(
                host_sections,
                mode=Mode.CHECKING,
            )
        )
