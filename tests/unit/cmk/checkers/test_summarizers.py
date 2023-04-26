#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# pylint: disable=undefined-variable
import pytest

from cmk.utils.exceptions import MKAgentError, MKTimeout
from cmk.utils.type_defs import ExitSpec, HostAddress, HostName

from cmk.checkers.checkresults import ActiveCheckResult
from cmk.checkers.summarize import summarize_failure, summarize_piggyback, summarize_success


class TestAgentSummarizer:
    def test_summarize_success(self) -> None:
        assert summarize_success(ExitSpec()) == [ActiveCheckResult(0, "Success")]

    def test_summarize_base_exception(self) -> None:
        assert summarize_failure(ExitSpec(), Exception()) == [ActiveCheckResult(3)]

    def test_summarize_MKAgentError_exception(self) -> None:
        assert summarize_failure(ExitSpec(), MKAgentError()) == [ActiveCheckResult(2)]

    def test_summarize_MKTimeout_exception(self) -> None:
        assert summarize_failure(ExitSpec(), MKTimeout()) == [ActiveCheckResult(2)]

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
            hostname=HostName("hostname"),
            ipaddress=HostAddress("1.2.3.4"),
            time_settings=[("", "", 0)],
            is_piggyback=False,
        ) == [ActiveCheckResult(0, "Success (but no data found for this host)")]

    def test_summarize_missing_data_with_is_piggyback_option(self) -> None:
        assert summarize_piggyback(
            hostname=HostName("hostname"),
            ipaddress=HostAddress("1.2.3.4"),
            time_settings=[("", "", 0)],
            is_piggyback=True,
        ) == [ActiveCheckResult(1, "Missing data")]

    @pytest.mark.skip("requires patching cmk.utils.piggyback :(")
    def test_summarize_existing_data_with_is_piggyback_option(self) -> None:
        assert summarize_piggyback(
            hostname=HostName("hostname"),
            ipaddress=HostAddress("1.2.3.4"),
            time_settings=[("", "", 0)],
            is_piggyback=True,
        ) == [ActiveCheckResult(0, "success"), ActiveCheckResult(0, "success")]
