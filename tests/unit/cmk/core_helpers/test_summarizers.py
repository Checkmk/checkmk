#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# pylint: disable=undefined-variable
import pytest  # type: ignore[import]

from cmk.utils.exceptions import MKAgentError, MKEmptyAgentData, MKTimeout
from cmk.utils.piggyback import PiggybackRawDataInfo
from cmk.utils.type_defs import AgentRawData, ExitSpec

import cmk.core_helpers.piggyback
from cmk.core_helpers.agent import AgentHostSections, AgentSummarizer, AgentSummarizerDefault
from cmk.core_helpers.piggyback import PiggybackSummarizer
from cmk.core_helpers.type_defs import Mode


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


class TestAgentSummarizerDefault_AllModes:
    @pytest.fixture
    def summarizer(self):
        return AgentSummarizerDefault(
            ExitSpec(),
            is_cluster=False,
            agent_min_version=0,
            agent_target_version=None,
            only_from=None,
        )

    @pytest.fixture(params=Mode)
    def mode(self, request):
        return request.param

    def test_missing_section(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(None, mode=mode) == (
            0,
            "Version: unknown, OS: unknown",
            [],
        )

    def test_random_section(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [["some_random", "data"], ["that_does", "nothing"]],
            mode=mode,
        ) == (
            0,
            "Version: unknown, OS: unknown",
            [],
        )

    def test_clear_version_and_os(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [["version:"], ["agentos:"]],
            mode=mode,
        ) == (
            0,
            "",
            [],
        )

    def test_set_version_and_os(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [["version:", "42"], ["agentos:", "BeOS", "or", "Haiku", "OS"]],
            mode=mode,
        ) == (
            0,
            "Version: 42, OS: BeOS or Haiku OS",
            [],
        )


class TestAgentSummarizerDefault_OnlyFrom:
    @pytest.fixture
    def summarizer(self):
        return AgentSummarizerDefault(
            ExitSpec(),
            is_cluster=False,
            agent_min_version=0,
            agent_target_version=None,
            only_from=["deep_space"],
        )

    @pytest.fixture
    def mode(self):
        # Only Mode.CHECKING triggers check_only_from
        return Mode.CHECKING

    def test_allowed(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:"],
                ["agentos:"],
                ["onlyfrom:", "deep_space"],
            ],
            mode=mode,
        ) == (0, "Allowed IP ranges: deep_space", [])

    def test_exceeding(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:"],
                ["agentos:"],
                ["onlyfrom:", "deep_space somewhere_else"],
            ],
            mode=mode,
        ) == (1, "Unexpected allowed IP ranges (exceeding: somewhere_else)(!)", [])

    def test_exceeding_missing(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:"],
                ["agentos:"],
                ["onlyfrom:", "somewhere_else"],
            ],
            mode=mode,
        ) == (
            1,
            "Unexpected allowed IP ranges (exceeding: somewhere_else, missing: deep_space)(!)",
            [],
        )


class TestAgentSummarizerDefault_CheckVersion:
    # TODO(ml): This is incomplete.
    @pytest.fixture
    def summarizer(self, request):
        return AgentSummarizerDefault(
            ExitSpec(),
            is_cluster=False,
            agent_min_version=0,
            agent_target_version=request.param,
            only_from=None,
        )

    @pytest.fixture
    def mode(self):
        # Only Mode.CHECKING triggers check_version
        return Mode.CHECKING

    @pytest.mark.parametrize("summarizer", ["42"], indirect=True)
    def test_match(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:", "42"],
                ["agentos:"],
            ],
            mode=mode,
        ) == (0, 'Version: 42', [])

    @pytest.mark.parametrize("summarizer", ["42"], indirect=True)
    def test_mismatch(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:", "69"],
                ["agentos:"],
            ],
            mode=mode,
        ) == (1, 'Version: 69, unexpected agent version 69 (should be 42)(!)', [])

    @pytest.mark.parametrize(
        "summarizer",
        [
            # This type of AgentTargetVersion does not seem to be handled at all.
            ("at_least", "0"),
            ("at_least", "333"),
            ("at_least", "random value"),
        ],
        indirect=True,
    )
    def test_at_least_str_success(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:", "69"],
                ["agentos:"],
            ],
            mode=mode,
        ) == (0, 'Version: 69', [])

    @pytest.mark.parametrize("summarizer", [("at_least", {})], indirect=True)
    def test_at_least_dict_empty(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:", "69"],
                ["agentos:"],
            ],
            mode=mode,
        ) == (0, 'Version: 69', [])


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
        return AgentHostSections(
            sections={},
            cache_info={},
            piggybacked_raw_data={"other": [b"line0", b"line1"]},
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
        assert summarizer.summarize_success(
            host_sections,
            mode=Mode.DISCOVERY,
        ) == (0, "", [])

    @pytest.mark.usefixtures("patch_get_piggyback_raw_data")
    def test_summarize_missing_data(self, summarizer, host_sections):
        assert summarizer.summarize_success(
            host_sections,
            mode=Mode.CHECKING,
        ) == (0, "", [])

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
        ) == (1, "Missing data", [])

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
        if summarizer.hostname is None or summarizer.ipaddress is None:
            reason = "success"
        else:
            reason = "success, success"

        assert summarizer.summarize_success(
            host_sections,
            mode=Mode.CHECKING,
        ) == (0, reason, [])
