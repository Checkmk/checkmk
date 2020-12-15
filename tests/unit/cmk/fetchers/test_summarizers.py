#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# pylint: disable=undefined-variable
import pytest  # type: ignore[import]

import cmk.utils.piggyback
from cmk.core_helpers.type_defs import Mode
from cmk.core_helpers.piggyback import PiggybackSummarizer
from cmk.core_helpers.agent import AgentHostSections


class TestPiggybackSummarizer:
    @pytest.fixture
    def summarizer(self):
        return PiggybackSummarizer(
            {},
            hostname="testhost",
            ipaddress=None,
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
            cmk.utils.piggyback,
            "get_piggyback_raw_data",
            lambda *args, **kwargs: (),
        )

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
