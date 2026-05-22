#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service
from cmk.legacy_checks import graylog_messages
from cmk.plugins.graylog import lib as graylog


def test_discovery_graylog_messages() -> None:
    info = [['{"events": 1000}']]
    parsed = graylog.deserialize_and_merge_json(info)
    assert list(graylog_messages.discover_graylog_messages(parsed)) == [Service()]


def test_check_graylog_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    info = [['{"events": 1000}']]
    parsed = graylog.deserialize_and_merge_json(info)
    params: dict[str, Any] = {}

    # Pre-populate value store to avoid GetRateError on first run
    monkeypatch.setattr(
        graylog,
        "get_value_store",
        lambda: {"graylog_msgs_avg.rate": (1670328674.09963, 900)},
    )

    results = list(graylog_messages.check_graylog_messages(params, parsed))

    summaries = [r.summary for r in results if isinstance(r, Result)]
    assert any("Total number of messages: 1000" in s for s in summaries)
    assert any("Average number of messages" in s and "30 minutes" in s for s in summaries)
    assert any("Total number of messages since last check" in s for s in summaries)

    metrics = {m.name: m.value for m in results if isinstance(m, Metric)}
    assert metrics["messages"] == 1000.0
    assert "msgs_avg" in metrics
    assert metrics["graylog_diff"] == 0.0
