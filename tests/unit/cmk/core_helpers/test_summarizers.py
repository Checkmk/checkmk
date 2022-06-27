#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# pylint: disable=undefined-variable
import json
from pathlib import Path
from typing import Final

import pytest

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import MKAgentError, MKEmptyAgentData, MKTimeout
from cmk.utils.piggyback import PiggybackFileInfo, PiggybackRawDataInfo
from cmk.utils.type_defs import AgentRawData, ExitSpec

import cmk.core_helpers.piggyback
from cmk.core_helpers import Summarizer as _Summarizer
from cmk.core_helpers.agent import AgentSummarizerDefault
from cmk.core_helpers.piggyback import PiggybackSummarizer

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


class Summarizer(_Summarizer):
    def summarize_success(self):
        return [ActiveCheckResult(0, "")]


class TestAgentSummarizer:
    @pytest.fixture
    def summarizer(self):
        return Summarizer(ExitSpec())

    def test_summarize_success(self, summarizer) -> None:
        assert summarizer.summarize_success() == [ActiveCheckResult(0)]

    def test_summarize_base_exception(self, summarizer) -> None:
        assert summarizer.summarize_failure(Exception()) == [ActiveCheckResult(3)]

    def test_summarize_MKEmptyAgentData_exception(self, summarizer) -> None:
        assert summarizer.summarize_failure(MKEmptyAgentData()) == [ActiveCheckResult(2)]

    def test_summarize_MKAgentError_exception(self, summarizer) -> None:
        assert summarizer.summarize_failure(MKAgentError()) == [ActiveCheckResult(2)]

    def test_summarize_MKTimeout_exception(self, summarizer) -> None:
        assert summarizer.summarize_failure(MKTimeout()) == [ActiveCheckResult(2)]


class TestAgentSummarizerDefault_AllModes:
    @pytest.fixture
    def summarizer(self):
        return AgentSummarizerDefault(ExitSpec())

    def test_missing_section(self, summarizer) -> None:
        assert summarizer.summarize_success() == [ActiveCheckResult(0, "Success")]

    def test_random_section(self, summarizer) -> None:
        assert summarizer.summarize_success() == [ActiveCheckResult(0, "Success")]


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
    def patch_get_piggyback_raw_data(self, monkeypatch):
        monkeypatch.setattr(
            cmk.core_helpers.piggyback,
            "get_piggyback_raw_data",
            lambda *args, **kwargs: (),
        )

    def test_repr_smoke_test(self, summarizer) -> None:
        assert isinstance(repr(summarizer), str)

    @pytest.mark.usefixtures("patch_get_piggyback_raw_data")
    def test_summarize_missing_data(self, summarizer) -> None:
        assert not summarizer.summarize_success()

    @pytest.mark.usefixtures("patch_get_piggyback_raw_data")
    def test_summarize_missing_data_with_always_option(
        self,
        summarizer,
        monkeypatch,
    ):
        monkeypatch.setattr(summarizer, "always", True)

        assert summarizer.summarize_success() == [ActiveCheckResult(1, "Missing data")]

    def test_summarize_existing_data_with_always_option(
        self,
        summarizer,
        monkeypatch,
    ):
        def get_piggyback_raw_data(source_hostname, time_settings):
            if not source_hostname:
                return ()
            return [
                PiggybackRawDataInfo(
                    PiggybackFileInfo(
                        source_hostname=source_hostname,
                        file_path=Path("/dev/null"),
                        successfully_processed=True,
                        message="success",
                        status=0,
                    ),
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

        assert all(r == ActiveCheckResult(0, "success") for r in summarizer.summarize_success())
