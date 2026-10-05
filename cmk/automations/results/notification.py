#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Notification-related automation results."""

from ast import literal_eval
from dataclasses import asdict, dataclass
from typing import override, Self

from cmk.automations.internal import AutomationID, AutomationResult
from cmk.automations.results._base import result_type_registry
from cmk.events.notify_types import NotifyAnalysisInfo, NotifyBulks


@dataclass
class NotificationReplayResult(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notification-replay")


result_type_registry.register(NotificationReplayResult)


@dataclass
class NotificationAnalyseResult(AutomationResult):
    result: NotifyAnalysisInfo | None

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notification-analyse")


result_type_registry.register(NotificationAnalyseResult)


@dataclass
class NotificationTestResult(AutomationResult):
    result: NotifyAnalysisInfo | None

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notification-test")


result_type_registry.register(NotificationTestResult)


@dataclass
class NotificationGetBulksResult(AutomationResult):
    result: NotifyBulks

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notification-get-bulks")


result_type_registry.register(NotificationGetBulksResult)


@dataclass
class NotifyResult(AutomationResult):
    exit_code: int | None
    output: str

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("notify")

    @classmethod
    @override
    def deserialize(cls, serialized_result: str) -> Self:
        return cls(**literal_eval(serialized_result))

    @override
    def serialize(
        self,
        for_cmk_version: str,
    ) -> str:
        return str(asdict(self))


result_type_registry.register(NotifyResult)
