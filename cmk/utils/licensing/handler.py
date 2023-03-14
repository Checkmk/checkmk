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
    EXPIRED = auto()


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

    def _get_num_services_for_trial_or_free(self):
        raise NotImplementedError()

    def effect_core(self, num_services: int) -> UserEffect:
        if (license_state := self.state) is LicenseState.TRIAL:
            return self._get_trial_user_effect(num_services)
        if license_state is LicenseState.FREE:
            return self._get_free_user_effect(num_services, [])
        if license_state is LicenseState.LICENSED:
            return self._get_licensed_user_effect()
        if license_state is LicenseState.EXPIRED:
            return self._get_expired_user_effect()
        raise NotImplementedError()

    def effect(self, changes: PendingChanges | None = None) -> UserEffect:
        if (license_state := self.state) is LicenseState.TRIAL:
            return self._get_trial_user_effect(self._get_num_services_for_trial_or_free())
        if license_state is LicenseState.FREE:
            return self._get_free_user_effect(
                self._get_num_services_for_trial_or_free(), changes if changes else []
            )
        if license_state is LicenseState.LICENSED:
            return self._get_licensed_user_effect()
        if license_state is LicenseState.EXPIRED:
            return self._get_expired_user_effect()
        raise NotImplementedError()

    def _get_trial_user_effect(self, num_services: int) -> UserEffect:
        raise NotImplementedError()

    def _get_free_user_effect(self, num_services: int, changes: PendingChanges) -> UserEffect:
        raise NotImplementedError()

    def _get_licensed_user_effect(self) -> UserEffect:
        raise NotImplementedError()

    def _get_expired_user_effect(self) -> UserEffect:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def notification_handler(self) -> NotificationHandler:
        raise NotImplementedError()
