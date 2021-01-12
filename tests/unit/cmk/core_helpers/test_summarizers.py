#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# pylint: disable=undefined-variable
import pytest  # type: ignore[import]

from cmk.utils.piggyback import PiggybackRawDataInfo
from cmk.utils.type_defs import AgentRawData

import cmk.core_helpers.piggyback
from cmk.core_helpers.agent import AgentHostSections
from cmk.core_helpers.piggyback import PiggybackSummarizer
from cmk.core_helpers.type_defs import Mode


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
