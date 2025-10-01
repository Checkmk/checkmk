#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal, override

from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId


@dataclass(frozen=True)
class Command(ABC):
    type Arguments = int | str | datetime | bool | list[int] | Enum | None

    @abstractmethod
    def name(self) -> str:
        """Name of the command to be sent."""

    @abstractmethod
    def args(self) -> list[Arguments]:
        """Arguments for the command."""


@dataclass(frozen=True)
class BaseAddComment(Command, ABC):
    host_name: HostName
    comment: str
    persistent: bool
    user: UserId


@dataclass(frozen=True)
class AddHostComment(BaseAddComment):
    @override
    def name(self) -> str:
        return "ADD_HOST_COMMENT"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.persistent, self.user, self.comment]


@dataclass(frozen=True)
class AddServiceComment(BaseAddComment):
    description: str

    @override
    def name(self) -> str:
        return "ADD_SVC_COMMENT"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description, self.persistent, self.user, self.comment]


@dataclass(frozen=True)
class BaseDeleteComment(Command, ABC):
    comment_id: int


@dataclass(frozen=True)
class DeleteServiceComment(BaseDeleteComment):
    @override
    def name(self) -> str:
        return "DEL_SVC_COMMENT"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.comment_id]


@dataclass(frozen=True)
class DeleteHostComment(BaseDeleteComment):
    @override
    def name(self) -> str:
        return "DEL_HOST_COMMENT"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.comment_id]


class Acknowledgement(Enum):
    NONE = 0
    NORMAL = 1
    STICKY = 2


@dataclass(frozen=True)
class AcknowledgeHostProblem(Command):
    host_name: HostName
    acknowledgement: Acknowledgement
    notify: bool = False
    persistent: bool = False
    user: UserId = UserId.builtin()
    comment: str | None = None
    expire_on: datetime | None = None

    @override
    def name(self) -> str:
        return "ACKNOWLEDGE_HOST_PROBLEM"

    @override
    def args(self) -> list[Command.Arguments]:
        return [
            self.host_name,
            self.acknowledgement,
            self.notify,
            self.persistent,
            self.user,
            self.comment,
            self.expire_on,
        ]


@dataclass(frozen=True)
class AcknowledgeServiceProblem(Command):
    host_name: HostName
    description: str
    acknowledgement: Acknowledgement
    notify: bool = False
    persistent: bool = False
    user: UserId = UserId.builtin()
    comment: str | None = None
    expire_on: datetime | None = None

    @override
    def name(self) -> str:
        return "ACKNOWLEDGE_SVC_PROBLEM"

    @override
    def args(self) -> list[Command.Arguments]:
        return [
            self.host_name,
            self.description,
            self.acknowledgement,
            self.notify,
            self.persistent,
            self.user,
            self.comment,
            self.expire_on,
        ]


@dataclass(frozen=True)
class BaseRemoveAcknowledgement(Command, ABC):
    host_name: HostName


@dataclass(frozen=True)
class RemoveHostAcknowledgement(BaseRemoveAcknowledgement):
    @override
    def name(self) -> str:
        return "REMOVE_HOST_ACKNOWLEDGEMENT"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name]


@dataclass(frozen=True)
class RemoveServiceAcknowledgement(BaseRemoveAcknowledgement):
    description: str

    @override
    def name(self) -> str:
        return "REMOVE_SVC_ACKNOWLEDGEMENT"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description]


@dataclass(frozen=True)
class BaseModifyDowntime(Command, ABC):
    downtime_id: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    recur_mode: int | None = None
    trigger_id: int | None = None
    duration: int | None = None
    user: UserId = UserId.builtin()
    comment: str | None = None


@dataclass(frozen=True)
class ModifyHostDowntime(BaseModifyDowntime):
    @override
    def name(self) -> str:
        return "MODIFY_HOST_DOWNTIME"

    @override
    def args(self) -> list[Command.Arguments]:
        return [
            self.downtime_id,
            self.start_time,
            self.end_time,
            self.recur_mode,
            self.trigger_id,
            self.duration,
            self.user,
            self.comment,
        ]


@dataclass(frozen=True)
class ModifyServiceDowntime(BaseModifyDowntime):
    @override
    def name(self) -> str:
        return "MODIFY_SVC_DOWNTIME"

    @override
    def args(self) -> list[Command.Arguments]:
        return [
            self.downtime_id,
            self.start_time,
            self.end_time,
            self.recur_mode,
            self.trigger_id,
            self.duration,
            self.user,
            self.comment,
        ]


@dataclass(frozen=True)
class BaseScheduleDowntime(Command, ABC):
    host_name: HostName
    start_time: datetime
    end_time: datetime
    recur_mode: int
    trigger_id: int
    duration: int
    user: UserId
    comment: str


@dataclass(frozen=True)
class ScheduleHostDowntime(BaseScheduleDowntime):
    @override
    def name(self) -> str:
        return "SCHEDULE_HOST_DOWNTIME"

    @override
    def args(self) -> list[Command.Arguments]:
        return [
            self.host_name,
            self.start_time,
            self.end_time,
            self.recur_mode,
            self.trigger_id,
            self.duration,
            self.user,
            self.comment,
        ]


@dataclass(frozen=True)
class ScheduleServiceDowntime(BaseScheduleDowntime):
    description: str

    @override
    def name(self) -> str:
        return "SCHEDULE_SVC_DOWNTIME"

    @override
    def args(self) -> list[Command.Arguments]:
        return [
            self.host_name,
            self.description,
            self.start_time,
            self.end_time,
            self.recur_mode,
            self.trigger_id,
            self.duration,
            self.user,
            self.comment,
        ]


@dataclass(frozen=True)
class BaseDeleteDowntime(Command, ABC):
    downtime_id: int


@dataclass(frozen=True)
class DeleteHostDowntime(BaseDeleteDowntime):
    @override
    def name(self) -> str:
        return "DEL_HOST_DOWNTIME"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.downtime_id]


@dataclass(frozen=True)
class DeleteServiceDowntime(BaseDeleteDowntime):
    @override
    def name(self) -> str:
        return "DEL_SVC_DOWNTIME"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.downtime_id]


@dataclass(frozen=True)
class ECUpdate(Command):
    event_ids: list[int]
    acknowledgement: bool | None = None
    user: UserId = UserId.builtin()
    comment: str = ""
    contact: str = ""

    @override
    def name(self) -> str:
        return "EC_UPDATE"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.event_ids, self.user, self.acknowledgement, self.comment, self.contact]


@dataclass(frozen=True)
class ECChangeState(Command):
    event_ids: list[int]
    user: UserId
    state: int | None = None

    @override
    def name(self) -> str:
        return "EC_CHANGESTATE"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.event_ids, self.user, self.state]


@dataclass(frozen=True)
class ECDelete(Command):
    event_ids: list[int]
    user: UserId

    @override
    def name(self) -> str:
        return "EC_DELETE"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.event_ids, self.user]


@dataclass(frozen=True)
class ECResetCounters(Command):
    id: str | None = None

    @override
    def name(self) -> str:
        return "EC_RESETCOUNTERS"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.id]


@dataclass(frozen=True)
class ECAction(Command):
    event_ids: list[int]
    action_id: str
    user: UserId = UserId.builtin()

    @override
    def name(self) -> str:
        return "EC_ACTION"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.event_ids, self.user, self.action_id]


@dataclass(frozen=True)
class ECDeleteEventsOfHost(Command):
    host_name: HostName
    user: UserId = UserId.builtin()

    @override
    def name(self) -> str:
        return "EC_DELETE_EVENTS_OF_HOST"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.user]


@dataclass(frozen=True)
class BaseScheduleForcedCheck(Command, ABC):
    host_name: HostName
    check_time: datetime


@dataclass(frozen=True)
class ScheduleForcedHostCheck(BaseScheduleForcedCheck):
    @override
    def name(self) -> str:
        return "SCHEDULE_FORCED_HOST_CHECK"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.check_time]


@dataclass(frozen=True)
class ScheduleForcedServiceCheck(BaseScheduleForcedCheck):
    description: str

    @override
    def name(self) -> str:
        return "SCHEDULE_FORCED_SVC_CHECK"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description, self.check_time]


@dataclass(frozen=True)
class MKLogwatchAcknowledge(Command):
    host_name: HostName
    filename: str

    @override
    def name(self) -> str:
        return "MK_LOGWATCH_ACKNOWLEDGE"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.filename]


@dataclass(frozen=True)
class DisableEventHandlers(Command):
    @override
    def name(self) -> str:
        return "DISABLE_EVENT_HANDLERS"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class EnableEventHandlers(Command):
    @override
    def name(self) -> str:
        return "ENABLE_EVENT_HANDLERS"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class DisablePerformanceData(Command):
    @override
    def name(self) -> str:
        return "DISABLE_PERFORMANCE_DATA"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class EnablePerformanceData(Command):
    @override
    def name(self) -> str:
        return "ENABLE_PERFORMANCE_DATA"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class DisableFlapDetection(Command):
    @override
    def name(self) -> str:
        return "DISABLE_FLAP_DETECTION"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class EnableFlapDetection(Command):
    @override
    def name(self) -> str:
        return "ENABLE_FLAP_DETECTION"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class StopExecutingHostChecks(Command):
    @override
    def name(self) -> str:
        return "STOP_EXECUTING_HOST_CHECKS"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class StartExecutingHostChecks(Command):
    @override
    def name(self) -> str:
        return "START_EXECUTING_HOST_CHECKS"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class StopExecutingServiceChecks(Command):
    @override
    def name(self) -> str:
        return "STOP_EXECUTING_SVC_CHECKS"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class StartExecutingServiceChecks(Command):
    @override
    def name(self) -> str:
        return "START_EXECUTING_SVC_CHECKS"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class DisableNotifications(Command):
    @override
    def name(self) -> str:
        return "DISABLE_NOTIFICATIONS"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class EnableNotifications(Command):
    @override
    def name(self) -> str:
        return "ENABLE_NOTIFICATIONS"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class Log(Command):
    message: str

    @override
    def name(self) -> str:
        return "LOG"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.message]


@dataclass(frozen=True)
class ECSwitchMode(Command):
    mode: Literal["sync", "takeover"] = "sync"

    @override
    def name(self) -> str:
        return "EC_SWITCH_MODE"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.mode]


@dataclass(frozen=True)
class ECCreate(Command):
    message: str

    @override
    def name(self) -> str:
        return "EC_CREATE"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.message]


@dataclass(frozen=True)
class ECReload(Command):
    @override
    def name(self) -> str:
        return "EC_RELOAD"

    @override
    def args(self) -> list[Command.Arguments]:
        return []


@dataclass(frozen=True)
class EnableHostNotifications(Command):
    host_name: HostName

    @override
    def name(self) -> str:
        return "ENABLE_HOST_NOTIFICATIONS"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name]


@dataclass(frozen=True)
class DisableHostNotifications(Command):
    host_name: HostName

    @override
    def name(self) -> str:
        return "ENABLE_HOST_NOTIFICATIONS"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name]


@dataclass(frozen=True)
class EnableServiceNotifications(Command):
    host_name: HostName
    description: str

    @override
    def name(self) -> str:
        return "ENABLE_SVC_NOTIFICATIONS"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description]


@dataclass(frozen=True)
class DisableServiceNotifications(Command):
    host_name: HostName
    description: str

    @override
    def name(self) -> str:
        return "ENABLE_SVC_NOTIFICATIONS"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description]


@dataclass(frozen=True)
class EnableHostCheck(Command):
    host_name: HostName

    @override
    def name(self) -> str:
        return "ENABLE_HOST_CHECK"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name]


@dataclass(frozen=True)
class DisableHostCheck(Command):
    host_name: HostName

    @override
    def name(self) -> str:
        return "DISABLE_HOST_CHECK"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name]


@dataclass(frozen=True)
class EnableServiceCheck(Command):
    host_name: HostName
    description: str

    @override
    def name(self) -> str:
        return "ENABLE_SVC_CHECK"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description]


@dataclass(frozen=True)
class DisableServiceCheck(Command):
    host_name: HostName
    description: str

    @override
    def name(self) -> str:
        return "DISABLE_SVC_CHECK"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description]


@dataclass(frozen=True)
class EnablePassiveHostChecks(Command):
    host_name: HostName

    @override
    def name(self) -> str:
        return "ENABLE_PASSIVE_HOST_CHECKS"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name]


@dataclass(frozen=True)
class DisablePassiveHostChecks(Command):
    host_name: HostName

    @override
    def name(self) -> str:
        return "DISABLE_PASSIVE_HOST_CHECKS"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name]


@dataclass(frozen=True)
class EnablePassiveServiceChecks(Command):
    host_name: HostName
    description: str

    @override
    def name(self) -> str:
        return "ENABLE_PASSIVE_SVC_CHECKS"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description]


@dataclass(frozen=True)
class DisablePassiveServiceChecks(Command):
    host_name: HostName
    description: str

    @override
    def name(self) -> str:
        return "DISABLE_PASSIVE_SVC_CHECKS"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description]


@dataclass(frozen=True)
class ChangeHostModifiedAttributes(Command):
    host_name: HostName
    value: int

    @override
    def name(self) -> str:
        return "CHANGE_HOST_MODATTR"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.value]


@dataclass(frozen=True)
class ChangeServiceModifiedAttributes(Command):
    host_name: HostName
    value: int
    description: str

    @override
    def name(self) -> str:
        return "CHANGE_SVC_MODATTR"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description, self.value]


@dataclass(frozen=True)
class BaseProcessCheckResult(Command, ABC):
    host_name: HostName
    status_code: int | None
    plugin_output: str


@dataclass(frozen=True)
class ProcessHostCheckResult(BaseProcessCheckResult):
    @override
    def name(self) -> str:
        return "PROCESS_HOST_CHECK_RESULT"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.status_code, self.plugin_output]


@dataclass(frozen=True)
class ProcessServiceCheckResult(BaseProcessCheckResult):
    description: str

    @override
    def name(self) -> str:
        return "PROCESS_SERVICE_CHECK_RESULT"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description, self.status_code, self.plugin_output]


class NotificationOption(Enum):
    DEFAULT = 0
    BROADCAST = 1
    FORCED = 2
    INCREMENT = 4


@dataclass(frozen=True)
class BaseSendCustomNotification(Command):
    host_name: HostName
    option: NotificationOption
    author: UserId
    comment: str


@dataclass(frozen=True)
class SendCustomHostNotification(BaseSendCustomNotification):
    @override
    def name(self) -> str:
        return "SEND_CUSTOM_HOST_NOTIFICATION"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.option, self.author, self.comment]


@dataclass(frozen=True)
class SendCustomServiceNotification(BaseSendCustomNotification):
    description: str

    @override
    def name(self) -> str:
        return "SEND_CUSTOM_SVC_NOTIFICATION"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.host_name, self.description, self.option, self.author, self.comment]


@dataclass(frozen=True)
class DeleteCrashReport(Command):
    crash_id: str

    @override
    def name(self) -> str:
        return "DEL_CRASH_REPORT"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.crash_id]


@dataclass(frozen=True)
class Dummy(Command):
    arg: str

    @override
    def name(self) -> str:
        return "Dummy"

    @override
    def args(self) -> list[Command.Arguments]:
        return [self.arg]
