#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import override

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
    persistent: bool = False
    user: UserId = UserId.builtin()


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
    description: str = ""

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
    NORMAL = 1
    STICKY = 2


@dataclass(frozen=True)
class BaseAcknowledgeProblem(Command, ABC):
    host_name: HostName
    acknowledgement: Acknowledgement
    notify: bool = False
    persistent: bool = False
    user: UserId = UserId.builtin()
    comment: str | None = None
    expire_on: datetime | None = None


@dataclass(frozen=True)
class AcknowledgeHostProblem(BaseAcknowledgeProblem):
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
class AcknowledgeServiceProblem(BaseAcknowledgeProblem):
    description: str = ""

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
    end_time: str | None = None
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
    user: UserId = UserId.builtin()
    comment: str | None = None


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
    description: str | None = None

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
    acknowledgement: int
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
    state: int

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
