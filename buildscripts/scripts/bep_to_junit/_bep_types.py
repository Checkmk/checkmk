# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Build event stream types.

https://github.com/bazelbuild/bazel/blob/master/src/main/java/com/google/devtools/build/lib/buildeventstream/proto/build_event_stream.proto

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self, TypedDict


class ConfigurationId(TypedDict, total=False):
    id: str


class ActionCompletedId(TypedDict, total=False):
    primaryOutput: str
    label: str
    configuration: ConfigurationId


class TargetCompletedId(TypedDict):
    label: str


class TestResultId(TypedDict):
    label: str


class EventId(TypedDict, total=False):
    targetCompleted: TargetCompletedId
    testResult: TestResultId
    actionCompleted: ActionCompletedId


class FailureDetail(TypedDict, total=False):
    message: str


class TargetComplete(TypedDict, total=False):
    success: bool
    failureDetail: FailureDetail


class File(TypedDict, total=False):
    name: str
    uri: str


class TestResult(TypedDict, total=False):
    status: str
    statusDetails: str
    testActionOutput: list[File]
    testAttemptDurationMillis: str


class ActionExecuted(TypedDict, total=False):
    stderr: File
    startTime: str
    endTime: str


class BepEvent(TypedDict, total=False):
    id: EventId
    completed: TargetComplete
    testResult: TestResult
    action: ActionExecuted
    children: list[EventId]


@dataclass(frozen=True)
class ActionKey:
    primary_output: str
    label: str
    config_id: str

    @classmethod
    def from_action_completed_id(cls, action_id: ActionCompletedId) -> Self:
        return cls(
            primary_output=action_id.get("primaryOutput", ""),
            label=action_id.get("label", ""),
            config_id=action_id.get("configuration", {}).get("id", ""),
        )


type FailedBuilds = dict[str, BepEvent]
type FailedTests = dict[str, BepEvent]
type ActionStderr = dict[ActionKey, str]
type ActionTiming = dict[ActionKey, tuple[str, str]]
