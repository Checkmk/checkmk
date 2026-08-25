#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Notification-related automation results."""

from ast import literal_eval
from dataclasses import asdict, dataclass
from typing import override, Self

from cmk.automations.results._base import (
    ABCAutomationResult,
    result_type_registry,
    SerializedResult,
)
from cmk.ccc import version as cmk_version
from cmk.events.notify_types import NotifyAnalysisInfo, NotifyBulks

from ..types import AutomationID


@dataclass
class NotificationReplayResult(ABCAutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notification-replay")


result_type_registry.register(NotificationReplayResult)


@dataclass
class NotificationAnalyseResult(ABCAutomationResult):
    result: NotifyAnalysisInfo | None

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notification-analyse")


result_type_registry.register(NotificationAnalyseResult)


@dataclass
class NotificationTestResult(ABCAutomationResult):
    result: NotifyAnalysisInfo | None

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notification-test")


result_type_registry.register(NotificationTestResult)


@dataclass
class NotificationGetBulksResult(ABCAutomationResult):
    result: NotifyBulks

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notification-get-bulks")


result_type_registry.register(NotificationGetBulksResult)


@dataclass
class NotifyResult(ABCAutomationResult):
    exit_code: int | None
    output: str

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notify")

    @classmethod
    @override
    def deserialize(cls, serialized_result: SerializedResult) -> Self:
        return cls(**literal_eval(serialized_result))

    @override
    def serialize(
        self,
        for_cmk_version: cmk_version.Version,  # used to stay compatible with older central sites
    ) -> SerializedResult:
        return SerializedResult(asdict(self))


result_type_registry.register(NotifyResult)
