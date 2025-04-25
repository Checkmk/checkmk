#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

import pytest

from cmk.ccc.exceptions import MKAgentError, MKTimeout
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.sectionname import SectionName

from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.parser import HostSections
from cmk.checkengine.summarize import summarize_failure, summarize_piggyback, summarize_success

from cmk.piggyback.backend import PiggybackMetaData


class TestAgentSummarizer:
    def test_summarize_success(self) -> None:
        assert summarize_success(ExitSpec()) == [ActiveCheckResult(state=0, summary="Success")]

    def test_summarize_base_exception(self) -> None:
        assert summarize_failure(ExitSpec(), Exception()) == [ActiveCheckResult(state=3)]

    def test_summarize_MKAgentError_exception(self) -> None:
        assert summarize_failure(ExitSpec(), MKAgentError()) == [ActiveCheckResult(state=2)]

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


class TestPiggybackSummarizer:
    def test_summarize_missing_data_without_is_piggyback_option(self) -> None:
        assert summarize_piggyback(
            host_sections=HostSections({}),
            hostname=HostName("hostname"),
            ipaddress=HostAddress("1.2.3.4"),
            time_settings=[(("regular_expression", ""), "", 0)],
            expect_data=False,
        ) == [ActiveCheckResult(state=0, summary="Success (but no data found for this host)")]

    def test_summarize_missing_data_with_is_piggyback_option(self) -> None:
        assert summarize_piggyback(
            host_sections=HostSections({}),
            hostname=HostName("hostname"),
            ipaddress=HostAddress("1.2.3.4"),
            time_settings=[(("regular_expression", ""), "", 0)],
            expect_data=True,
        ) == [ActiveCheckResult(state=1, summary="Missing data")]

    @pytest.mark.parametrize("expect_data", [True, False])
    def test_summarize_outdated_data_regardless_of_is_piggyback_option(
        self, expect_data: bool
    ) -> None:
        now = int(time.time())
        assert summarize_piggyback(
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
            hostname=HostName("hostname"),
            ipaddress=HostAddress("1.2.3.4"),
            time_settings=[(None, "max_cache_age", 10)],
            expect_data=expect_data,
            now=now,
        ) == [
            ActiveCheckResult(
                state=0, summary="Piggyback data outdated (age: 0:00:20, allowed: 0:00:10)"
            )
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
            hostname=HostName("hostname"),
            ipaddress=HostAddress("1.2.3.4"),
            time_settings=[(None, "max_cache_age", 10)],
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
            hostname=HostName("hostname"),
            ipaddress=HostAddress("1.2.3.4"),
            time_settings=[
                (None, "max_cache_age", 10),
                (None, "validity_period", 30),
                (None, "validity_state", 2),
            ],
            expect_data=expect_data,
            now=now,
        ) == [
            ActiveCheckResult(
                state=2,
                summary="Piggyback data not updated by source 'source' (still valid, 0:00:28 left)",
            ),
        ]
