# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""BEP parsing: extract failed builds, failed tests, and action stderr URIs."""

from __future__ import annotations

import json
from collections.abc import Iterable

from ._bep_types import ActionKey, ActionStderr, ActionTiming, BepEvent, FailedBuilds, FailedTests


def parse_bep(bep: Iterable[str]) -> tuple[FailedBuilds, FailedTests, ActionStderr, ActionTiming]:
    all_failed_targets: dict[str, BepEvent] = {}
    test_labels: set[str] = set()
    failed_tests: dict[str, BepEvent] = {}
    action_stderr_uris: dict[ActionKey, str] = {}
    action_timing: dict[ActionKey, tuple[str, str]] = {}

    for raw in bep:
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue

        eid = event.get("id", {})
        if "targetCompleted" in eid:
            if event.get("aborted", {}).get("reason") == "SKIPPED":
                pass
            elif not event.get("completed", {}).get("success", False):
                all_failed_targets[eid["targetCompleted"]["label"]] = event
        elif "testResult" in eid:
            label = eid["testResult"]["label"]
            test_labels.add(label)
            if event.get("testResult", {}).get("status") == "FAILED":
                failed_tests[label] = event
        elif "actionCompleted" in eid:
            key = ActionKey.from_action_completed_id(eid["actionCompleted"])
            action = event.get("action", {})
            action_stderr_uris[key] = action.get("stderr", {}).get("uri", "")
            if (t_start := action.get("startTime", "")) and (t_end := action.get("endTime", "")):
                action_timing[key] = (t_start, t_end)

    return (
        {label: ev for label, ev in all_failed_targets.items() if label not in test_labels},
        failed_tests,
        action_stderr_uris,
        action_timing,
    )
