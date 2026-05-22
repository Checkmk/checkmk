#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

from cmk.agent_based.v2 import Result, Service, State
from cmk.legacy_checks.graylog_license import (
    check_graylog_license,
    discover_graylog_license,
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json


def test_discovery_graylog_license() -> None:
    info = [
        ['{"status": [{"valid": true, "expired": false, "violated": false}]}'],
    ]
    parsed = deserialize_and_merge_json(info)
    assert list(discover_graylog_license(parsed)) == [Service()]


def test_check_graylog_license() -> None:
    info = [
        [
            '{"status": [{"expired": false, "violated": false, "valid": true, "traffic_exceeded": false, "cluster_not_covered": false, "nodes_exceeded": false, "remote_checks_failed": false, "license": {"traffic_limit": 5368709120, "expiration_date": "2024-12-31T23:59:59Z", "subject": "/license/enterprise", "trial": false, "enterprise": {"require_remote_check": true}}}]}'
        ],
    ]
    parsed = deserialize_and_merge_json(info)
    params: dict[str, Any] = {}

    summaries = [r.summary for r in check_graylog_license(params, parsed) if isinstance(r, Result)]
    assert "Is expired: no" in summaries
    assert "Is violated: no" in summaries
    assert "Is valid: yes" in summaries
    assert "Traffic is exceeded: no" in summaries
    assert "Cluster is not covered: no" in summaries
    assert "Nodes exceeded: no" in summaries
    assert "Remote checks failed: no" in summaries
    assert any("Expires in" in s for s in summaries)
    assert "Subject: /license/enterprise" in summaries
    assert "Trial: no" in summaries
    assert "Requires remote checks: yes" in summaries


def test_check_graylog_license_no_enterprise() -> None:
    info = [['{"status": []}']]
    parsed = deserialize_and_merge_json(info)
    assert list(check_graylog_license({"no_enterprise": 1}, parsed)) == [
        Result(state=State.WARN, summary="No enterprise license found"),
    ]
