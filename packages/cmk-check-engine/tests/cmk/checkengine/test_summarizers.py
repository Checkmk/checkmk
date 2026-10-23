#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import time
from collections.abc import Mapping

import pytest

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import MKTimeout
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetcher_abc import FetcherError
from cmk.checkengine.helper_interface import FetcherType
from cmk.checkengine.parser import AgentRawDataSection, HostSections
from cmk.checkengine.plugins import SectionName
from cmk.checkengine.specs.checkresults import ActiveCheckResult
from cmk.checkengine.specs.exitspec import ExitSpec
from cmk.checkengine.summarize import (
    summarize,
    summarize_failure,
    summarize_piggyback,
    summarize_success,
    SummaryConfig,
)
from cmk.piggyback.backend import Config as PiggybackConfig
from cmk.piggyback.backend import PiggybackMetaData
from cmk.server_side_programs.v1 import AgentMessages


def _messages_sections(*rows: Mapping[str, str]) -> HostSections[AgentRawDataSection]:
    return HostSections(
        {SectionName(AgentMessages.SECTION_NAME): [[json.dumps(row)] for row in rows]}
    )


def _warning(message: str) -> Mapping[str, str]:
    return {"level": "warning", "message": message}


def _info(message: str) -> Mapping[str, str]:
    return {"level": "info", "message": message}


class TestAgentSummarizer:
    def test_summarize_success(self) -> None:
        assert summarize_success(HostSections({}), ExitSpec()) == [
            ActiveCheckResult(state=0, summary="Success")
        ]

    def test_summarize_base_exception(self) -> None:
        assert summarize_failure(ExitSpec(), Exception()) == [ActiveCheckResult(state=3)]

    def test_summarize_MKAgentError_exception(self) -> None:
        assert summarize_failure(ExitSpec(), FetcherError()) == [ActiveCheckResult(state=2)]

    def test_summarize_MKTimeout_exception(self) -> None:
        assert summarize_failure(ExitSpec(), MKTimeout()) == [ActiveCheckResult(state=2)]

    def test_summarize_multiline_exception(self) -> None:
        assert summarize_failure(
            ExitSpec(),
            RuntimeError("detail line 1\ndetail line 2\nexpected summary line"),
        ) == [
            ActiveCheckResult(
                state=3,
                summary="expected summary line",
                details=["detail line 1", "detail line 2", "expected summary line"],
            )
        ]

    def test_no_messages_section_is_success(self) -> None:
        assert summarize_success(HostSections({}), ExitSpec()) == [
            ActiveCheckResult(state=0, summary="Success")
        ]

    def test_each_message_is_one_result_in_order(self) -> None:
        assert summarize_success(
            _messages_sections(_info("first"), _warning("second"), {"message": "third"}),
            ExitSpec(),
        ) == [
            ActiveCheckResult(state=0, summary="Success"),
            ActiveCheckResult(state=0, summary="first"),
            ActiveCheckResult(state=1, summary="second"),
            ActiveCheckResult(state=1, summary="third"),
        ]

    def test_multi_line_message_shows_first_line_in_summary(self) -> None:
        assert summarize_success(
            _messages_sections(_warning("first line\nsecond line")), ExitSpec()
        )[1] == ActiveCheckResult(
            state=1, summary="first line", details=["first line", "second line"]
        )

    def test_empty_message_is_shown_as_unspecified(self) -> None:
        assert summarize_success(_messages_sections(_info(""), _warning("")), ExitSpec())[1:] == [
            ActiveCheckResult(state=0, summary="Unspecified info"),
            ActiveCheckResult(state=1, summary="Unspecified warning"),
        ]

    @pytest.mark.parametrize("configured_state", [0, 2])
    def test_warning_state_is_taken_from_exit_spec(self, configured_state: int) -> None:
        assert (
            summarize_success(
                _messages_sections(_warning("first")),
                ExitSpec(warnings=configured_state),
            )[1].state
            == configured_state
        )

    def test_info_is_ok_regardless_of_configured_warning_state(self) -> None:
        assert (
            summarize_success(_messages_sections(_info("first")), ExitSpec(warnings=2))[1].state
            == 0
        )

    def test_summarize_dispatches_special_agent_sections(self) -> None:
        assert summarize(
            result.OK(_messages_sections(_warning("first"))),
            SummaryConfig(
                exit_spec=ExitSpec(warnings=2),
                piggyback_config=PiggybackConfig(HostName("hostname"), []),
                expect_data=False,
            ),
            fetcher_type=FetcherType.SPECIAL_AGENT,
        ) == [
            ActiveCheckResult(state=0, summary="Success"),
            ActiveCheckResult(state=2, summary="first"),
        ]

    def test_summarize_dispatches_special_agent_failure(self) -> None:
        assert summarize(
            result.Error(FetcherError("boom")),
            SummaryConfig(
                exit_spec=ExitSpec(connection=1),
                piggyback_config=PiggybackConfig(HostName("hostname"), []),
                expect_data=False,
            ),
            fetcher_type=FetcherType.SPECIAL_AGENT,
        ) == [ActiveCheckResult(state=1, summary="boom")]


class TestPiggybackSummarizer:
    def test_summarize_missing_data_without_is_piggyback_option(self) -> None:
        assert summarize_piggyback(
            host_sections=HostSections({}),
            config=PiggybackConfig(HostName("hostname"), [(("regular_expression", ""), "", 0)]),
            expect_data=False,
        ) == [ActiveCheckResult(state=0, summary="Success (but no data found for this host)")]

    def test_summarize_missing_data_with_is_piggyback_option(self) -> None:
        assert summarize_piggyback(
            host_sections=HostSections({}),
            config=PiggybackConfig(HostName("hostname"), [(("regular_expression", ""), "", 0)]),
            expect_data=True,
        ) == [ActiveCheckResult(state=1, summary="Missing data")]

    @pytest.mark.parametrize(
        "expect_data, expected_results",
        [
            # When the host is not flagged as a piggyback host, keep the lenient
            # state-0 semantic: no data is treated like no problem.
            pytest.param(
                False,
                [
                    ActiveCheckResult(
                        state=0, summary="Piggyback data outdated (age: 0:00:20, allowed: 0:00:10)"
                    )
                ],
                id="expected=False",
            ),
            # When the host IS a piggyback host, outdated data is a real issue and
            # discovery should not act destructively on it -> WARN (state 1).
            pytest.param(
                True,
                [
                    ActiveCheckResult(
                        state=0, summary="Piggyback data outdated (age: 0:00:20, allowed: 0:00:10)"
                    ),
                    ActiveCheckResult(state=1, summary="All piggyback data sources outdated."),
                ],
                id="expected=True",
            ),
        ],
    )
    def test_summarize_outdated_data_state_depends_on_is_piggyback_option(
        self, expect_data: bool, expected_results: list[ActiveCheckResult]
    ) -> None:
        now = int(time.time())
        assert (
            summarize_piggyback(
                host_sections=HostSections(
                    {
                        SectionName("piggyback_source_summary"): [
                            [
                                PiggybackMetaData(
                                    source=HostAddress("source"),
                                    piggybacked=HostName("hostname"),
                                    last_update=now - 20,
                                    last_contact=now - 10,
                                ).serialize()
                            ]
                        ],
                    }
                ),
                config=PiggybackConfig(HostName("hostname"), [(None, "max_cache_age", 10)]),
                expect_data=expect_data,
                now=now,
            )
            == expected_results
        )

    def test_summarize_outdated_data_with_fresh_source_does_not_add_aggregate_warning(
        self,
    ) -> None:
        # Container/VM moved between source hosts: the old source's piggyback
        # file is still on disk but stale, while the new source provides
        # fresh data. The aggregate WARN MUST NOT be added in this case --
        # discovery has to be able to proceed to transition the host to the
        # new source rather than wait for the daily piggyback cleanup job.
        now = int(time.time())
        assert summarize_piggyback(
            host_sections=HostSections(
                {
                    SectionName("piggyback_source_summary"): [
                        [
                            PiggybackMetaData(
                                source=HostAddress("old_source"),
                                piggybacked=HostName("hostname"),
                                last_update=now - 20,
                                last_contact=now - 10,
                            ).serialize()
                        ],
                        [
                            PiggybackMetaData(
                                source=HostAddress("new_source"),
                                piggybacked=HostName("hostname"),
                                last_update=now,
                                last_contact=now - 1,
                            ).serialize()
                        ],
                    ],
                }
            ),
            config=PiggybackConfig(HostName("hostname"), [(None, "max_cache_age", 10)]),
            expect_data=True,
            now=now,
        ) == [
            ActiveCheckResult(
                state=0,
                summary="Piggyback data outdated (age: 0:00:20, allowed: 0:00:10)",
            ),
            ActiveCheckResult(state=0, summary="Successfully processed from source 'new_source'"),
        ]

    @pytest.mark.parametrize("expect_data", [True, False])
    def test_summarize_abandoned_data_without_tolerance_regardless_of_is_piggyback_option(
        self, expect_data: bool
    ) -> None:
        now = 123456789  # any time is fine
        assert summarize_piggyback(
            host_sections=HostSections(
                {
                    SectionName("piggyback_source_summary"): [
                        [
                            PiggybackMetaData(
                                source=HostAddress("source"),
                                piggybacked=HostName("hostname"),
                                last_update=now - 2,
                                last_contact=now - 1,
                            ).serialize()
                        ]
                    ],
                }
            ),
            config=PiggybackConfig(HostName("hostname"), [(None, "max_cache_age", 10)]),
            expect_data=expect_data,
            now=now,
        ) == [ActiveCheckResult(state=0, summary="Piggyback data not updated by source 'source'")]

    @pytest.mark.parametrize("expect_data", [True, False])
    def test_summarize_abandoned_data_with_tolerance_regardless_of_is_piggyback_option(
        self, expect_data: bool
    ) -> None:
        now = 123456789  # any time is fine
        assert summarize_piggyback(
            host_sections=HostSections(
                {
                    SectionName("piggyback_source_summary"): [
                        [
                            PiggybackMetaData(
                                source=HostAddress("source"),
                                piggybacked=HostName("hostname"),
                                last_update=now - 2,
                                last_contact=now - 1,
                            ).serialize()
                        ]
                    ],
                }
            ),
            config=PiggybackConfig(
                HostName("hostname"),
                [
                    (None, "max_cache_age", 10),
                    (None, "validity_period", 30),
                    (None, "validity_state", 2),
                ],
            ),
            expect_data=expect_data,
            now=now,
        ) == [
            ActiveCheckResult(
                state=2,
                summary="Piggyback data not updated by source 'source' (still valid, 0:00:28 left)",
            ),
        ]
