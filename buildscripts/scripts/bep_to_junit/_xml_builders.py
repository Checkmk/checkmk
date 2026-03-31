# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""XML builders for build failures and test failures."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ._bep_types import ActionKey, ActionStderr, ActionTiming, BepEvent
from ._helpers import action_duration_seconds, make_xml


def build_failure_xml(
    label: str,
    event: BepEvent,
    action_stderr: ActionStderr,
    action_timing: ActionTiming,
) -> ET.Element:
    """FAILED TO BUILD: use failureDetail message + child action stderr."""
    child_keys = [
        ActionKey.from_action_completed_id(action_id)
        for child in event.get("children", [])
        if (action_id := child.get("actionCompleted"))
    ]
    return make_xml(
        label,
        event.get("completed", {}).get("failureDetail", {}).get("message", "FAILED TO BUILD"),
        "\n\n".join(
            action_stderr[key].strip()
            for key in child_keys
            if key in action_stderr and action_stderr[key].strip()
        ),
        sum(
            action_duration_seconds(*action_timing[key])
            for key in child_keys
            if key in action_timing
        ),
    )


def test_failure_xml(label: str, event: BepEvent, log_content: str) -> ET.Element:
    """Test ran but FAILED: caller supplies test.log content."""
    result = event.get("testResult", {})
    return make_xml(
        label,
        result.get("statusDetails", "FAILED"),
        log_content,
        int(result.get("testAttemptDurationMillis", "0")) / 1000.0,
    )


def test_log_uri(event: BepEvent) -> str:
    """Return the test.log URI from a testResult event, or empty string."""
    return next(
        (
            o["uri"]
            for o in event.get("testResult", {}).get("testActionOutput", [])
            if o.get("name") == "test.log"
        ),
        "",
    )
