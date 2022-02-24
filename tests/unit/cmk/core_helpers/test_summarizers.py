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
        assert not summarizer.summarize_check_mk_section(None, mode=mode)

    def test_random_section(self, summarizer, mode):
        assert (
            summarizer.summarize_check_mk_section(
                [["some_random", "data"], ["that_does", "nothing"]],
                mode=mode,
            )
            == []
        )

    def test_clear_version_and_os(self, summarizer, mode):
        assert (
            summarizer.summarize_check_mk_section(
                [["version:"], ["agentos:"]],
                mode=mode,
            )
            == []
        )

    def test_set_version_and_os(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [["version:", "42"], ["agentos:", "BeOS", "or", "Haiku", "OS"]],
            mode=mode,
        ) == [
            ActiveCheckResult(0, "Version: 42"),
            ActiveCheckResult(0, "OS: BeOS or Haiku OS"),
        ]


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
                ["onlyfrom:", "deep_space"],
            ],
            mode=mode,
        ) == [ActiveCheckResult(0, "Allowed IP ranges: deep_space")]

    def test_exceeding(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["onlyfrom:", "deep_space somewhere_else"],
            ],
            mode=mode,
        ) == [ActiveCheckResult(1, "Unexpected allowed IP ranges (exceeding: somewhere_else)")]

    def test_exceeding_missing(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["onlyfrom:", "somewhere_else"],
            ],
            mode=mode,
        ) == [
            ActiveCheckResult(
                1,
                "Unexpected allowed IP ranges (exceeding: somewhere_else, missing: deep_space)",
            )
        ]

    @pytest.mark.parametrize("state", [0, 1, 2, 3])
    def test_configure_missmatch(self, mode, state):
        assert (
            AgentSummarizerDefault(
                ExitSpec(restricted_address_mismatch=state),
                is_cluster=False,
                agent_min_version=0,
                agent_target_version=None,
                only_from=["deep_space"],
            )
            .summarize_check_mk_section(
                [
                    ["onlyfrom:", "somewhere_else"],
                ],
                mode=mode,
            )[0]
            .state
            == state
        )


class TestAgentSummarizerDefault_FailedPythonPlugins:
    @pytest.fixture
    def summarizer(self):
        return AgentSummarizerDefault(
            ExitSpec(),
            is_cluster=False,
            agent_min_version=0,
            agent_target_version=None,
            only_from=None,
        )

    @pytest.fixture
    def mode(self):
        # Only Mode.CHECKING triggers _check_python_plugins
        return Mode.CHECKING

    def test_two_plugins_failed(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:"],
                ["agentos:"],
                ["FailedPythonPlugins:", "one"],
                ["FailedPythonPlugins:", "two"],
                ["FailedPythonReason:", "I'm not in the mood to execute python plugins"],
            ],
            mode=mode,
        ) == [
            ActiveCheckResult(
                1,
                "Failed to execute python plugins: one two"
                " (I'm not in the mood to execute python plugins)",
            )
        ]

    def test_no_plugins_failed(self, summarizer, mode):
        assert not summarizer.summarize_check_mk_section(
            [
                ["version:"],
                ["agentos:"],
                ["FailedPythonReason:", "I'm not in the mood to execute python plugins"],
            ],
            mode=mode,
        )


class TestAgentSummarizerDefault_Transport:
    @pytest.fixture
    def summarizer(self):
        return AgentSummarizerDefault(
            ExitSpec(),
            is_cluster=False,
            agent_min_version=0,
            agent_target_version=None,
            only_from=None,
        )

    @pytest.fixture
    def mode(self):
        # Only Mode.CHECKING triggers _check_transport
        return Mode.CHECKING

    def test_tls_ok(self, summarizer, mode):
        assert (
            summarizer.summarize_check_mk_section(
                [
                    ["AgentController:", "cmk-agent-ctl", "0.1.0"],
                    ["AgentControllerStatus:", *CONTROLLER_STATUS_REGISTERED],
                    ["SSHClient:"],
                ],
                mode=mode,
            )
            == []
        )

    def test_tls_not_active(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["AgentController:", "cmk-agent-ctl", "0.1.0"],
                ["AgentControllerStatus:", *CONTROLLER_STATUS_LEGACY],
                ["SSHClient:"],
            ],
            mode=mode,
        ) == [
            ActiveCheckResult(
                1,
                "TLS is not activated on monitored host (see details)",
                (
                    "The hosts agent supports TLS, but it is not being used.",
                    "We strongly recommend to enable TLS by registering the host to the site"
                    " (using the `cmk-agent-ctl register` command on the monitored host).",
                    "However you can configure missing TLS to be OK in the setting"
                    ' "State in case of available but not enabled TLS" of the ruleset'
                    ' "Status of the Checkmk services".',
                ),
            )
        ]

    def test_controller_not_available(self, summarizer, mode):
        assert (
            summarizer.summarize_check_mk_section(
                [
                    ["AgentController:"],
                ],
                mode=mode,
            )
            == []
        )

    def test_no_tls_but_ssh(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["AgentController:", "cmk-agent-ctl", "0.1.0"],
                ["AgentControllerStatus:", *CONTROLLER_STATUS_LEGACY],
                ["SSHClient:", "1.2.3.4"],
            ],
            mode=mode,
        ) == [ActiveCheckResult(0, "Transport via SSH")]


class TestAgentSummarizerDefault_Fails:
    @pytest.fixture
    def summarizer(self):
        return AgentSummarizerDefault(
            ExitSpec(),
            is_cluster=False,
            agent_min_version=0,
            agent_target_version=None,
            only_from=None,
        )

    @pytest.fixture
    def mode(self):
        # Only Mode.CHECKING triggers _check_agent_update
        return Mode.CHECKING

    def test_update_agent_fail(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:"],
                ["agentos:"],
                ["UpdateFailed:", "what"],
                ["UpdateRecoverAction:", "why"],
            ],
            mode=Mode.CHECKING,
        ) == [ActiveCheckResult(1, "what why")]

    def test_update_agent_success(self, summarizer, mode):
        assert not summarizer.summarize_check_mk_section(
            [
                ["version:"],
                ["agentos:"],
                ["UpdateFailed:", "what"],
            ],
            mode=mode,
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
        ) == [ActiveCheckResult(0, "Version: 42")]

    @pytest.mark.parametrize("summarizer", ["42"], indirect=True)
    def test_mismatch(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:", "69"],
                ["agentos:"],
            ],
            mode=mode,
        ) == [
            ActiveCheckResult(0, "Version: 69"),
            ActiveCheckResult(1, "unexpected agent version 69 (should be 42)"),
        ]

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
        ) == [ActiveCheckResult(0, "Version: 69")]

    @pytest.mark.parametrize("summarizer", [("at_least", {})], indirect=True)
    def test_at_least_dict_empty(self, summarizer, mode):
        assert summarizer.summarize_check_mk_section(
            [
                ["version:", "69"],
                ["agentos:"],
            ],
            mode=mode,
        ) == [ActiveCheckResult(0, "Version: 69")]


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
