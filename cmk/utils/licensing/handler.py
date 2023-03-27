#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from enum import auto, Enum


class LicenseState(Enum):
    """All possible license states of the Checkmk site"""

    TRIAL = auto()
    FREE = auto()
    LICENSED = auto()
    UNLICENSED = auto()


@dataclass
class EmailNotification:
    period: timedelta
    remaining_time: timedelta
    subject: str
    message: str


@dataclass
class HeaderNotification:
    roles: Sequence[str]
    message: str


@dataclass
class ActivationBlock:
    message: str


@dataclass
class UserEffect:
    header: HeaderNotification | None
    email: EmailNotification | None
    block: ActivationBlock | None


class NotificationHandler(abc.ABC):
    def __init__(self, email_notification: EmailNotification | None) -> None:
        self._email_notification = email_notification

    @abc.abstractmethod
    def manage_notification(self) -> None:
        raise NotImplementedError()


PendingChanges = Sequence[tuple]


class LicensingHandler(abc.ABC):
    @property
    @abc.abstractmethod
    def state(self) -> LicenseState:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def message(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def effect_core(self, num_services: int, num_hosts_shadow: int) -> UserEffect:
        raise NotImplementedError()

    @abc.abstractmethod
    def effect(self, changes: PendingChanges | None = None) -> UserEffect:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def notification_handler(self) -> NotificationHandler:
        raise NotImplementedError()
