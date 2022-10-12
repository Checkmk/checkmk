#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# pylint: disable=undefined-variable
import pytest

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import MKAgentError, MKEmptyAgentData, MKTimeout
from cmk.utils.type_defs import ExitSpec

from cmk.core_helpers.summarize import summarize_failure, summarize_piggyback, summarize_success


class TestAgentSummarizer:
    def test_summarize_success(self) -> None:
        assert summarize_success(ExitSpec()) == [ActiveCheckResult(0, "Success")]

    def test_summarize_base_exception(self) -> None:
        assert summarize_failure(ExitSpec(), Exception()) == [ActiveCheckResult(3)]

    def test_summarize_MKEmptyAgentData_exception(self) -> None:
        assert summarize_failure(ExitSpec(), MKEmptyAgentData()) == [ActiveCheckResult(2)]

    def test_summarize_MKAgentError_exception(self) -> None:
        assert summarize_failure(ExitSpec(), MKAgentError()) == [ActiveCheckResult(2)]

    def test_summarize_MKTimeout_exception(self) -> None:
        assert summarize_failure(ExitSpec(), MKTimeout()) == [ActiveCheckResult(2)]


class TestPiggybackSummarizer:
    def test_summarize_missing_data_without_is_piggyback_option(self) -> None:
        assert (
            summarize_piggyback(
                hostname="hostname",
                ipaddress="1.2.3.4",
                time_settings=[("", "", 0)],
                is_piggyback=False,
            )
            == []
        )

    def test_summarize_missing_data_with_is_piggyback_option(self) -> None:
        assert summarize_piggyback(
            hostname="hostname",
            ipaddress="1.2.3.4",
            time_settings=[("", "", 0)],
            is_piggyback=True,
        ) == [ActiveCheckResult(1, "Missing data")]

    @pytest.mark.skip("requires patching cmk.utils.piggyback :(")
    def test_summarize_existing_data_with_is_piggyback_option(self) -> None:
        assert summarize_piggyback(
            hostname="hostname",
            ipaddress="1.2.3.4",
            time_settings=[("", "", 0)],
            is_piggyback=True,
        ) == [ActiveCheckResult(0, "success"), ActiveCheckResult(0, "success")]
