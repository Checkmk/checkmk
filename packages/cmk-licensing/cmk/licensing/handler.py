#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from enum import auto, Enum
from pathlib import Path
from typing import NamedTuple

from cmk.ccc import store


class LicenseState(Enum):
    """All possible license states of the Checkmk site.

    Note that new enums may be added at any point, and the precise definitions of existing enums may
    change (e.g. which parts of Checkmk are supposed to work in which state). Therefore, please use
    the methods that are defined for each state, instead of matching the states themselves (i.e.
    instead of `state in [...]` use `state.is_...()`).

    The methods are intended to guard the site capabilities and apply other effects depending on the
    license state. This way, all the implications of licensed states are managed centrally.
    """

    # The site has no active license, but is still in the trial period, and the trial verification
    # workflow has been completed.
    TRIAL = auto()

    # The site has never had a license, and the trial period has expired.
    FREE = auto()

    # The site has a valid license that has been verified recently, or a recently expired license
    # and a grace period is in effect.
    LICENSED = auto()

    # The site used to have a valid license, but it expired and the grace period has elapsed.
    UNLICENSED = auto()

    # The site has no active license, but is still in the trial period. The user has selected "trial
    # mode" in the trial verification workflow, but has not completed the verification process.
    PENDING_TRIAL_VERIFICATION = auto()

    # The site has no active license, but is still in the trial period. The user has selected
    # "licensed mode", but did not completed the license verification process yet.
    PENDING_LICENSE_VERIFICATION = auto()

    # The site has no active license, but is still in the trial period. The user has not selected
    # whether the site should be in the "trial" or "licensed" mode in the trial verification
    # workflow yet.
    PENDING_SELECTION = auto()

    @property
    def readable(self) -> str:
        match self:
            case LicenseState.TRIAL:
                return "trial"
            case LicenseState.FREE:
                return "free"
            case LicenseState.LICENSED:
                return "licensed"
            case LicenseState.UNLICENSED:
                return "unlicensed"
            case LicenseState.PENDING_TRIAL_VERIFICATION:
                return "unverified trial"
            case LicenseState.PENDING_LICENSE_VERIFICATION:
                return "unverified licensed"
            case LicenseState.PENDING_SELECTION:
                return "trial mode not selected"
        raise ValueError(f"unexpected license state: {self!r}")

    def blocks_distributed_setup_changes_free(self) -> bool:
        """Returns True if the site should block distributed changes.

        This typically happens when the site enters a free state after a trial expiration."""

        return self is LicenseState.FREE

    def is_connecting_to_remotes_enabled(self) -> bool:
        """Returns True if distributed monitoring features should be enabled (for central sites)."""

        return self in [
            LicenseState.TRIAL,
            LicenseState.LICENSED,
            LicenseState.PENDING_SELECTION,
            LicenseState.PENDING_LICENSE_VERIFICATION,
            LicenseState.PENDING_TRIAL_VERIFICATION,
        ]

    def is_adding_as_remote_enabled(self) -> bool:
        """Returns True if the site can be added to a distributed monitoring setup (as a remote site)."""

        # Note: it's not clear if UNLICENSED remote sites should be prevented from remote site
        # automation. This code replicates the behaviour that existed in the past, however, it
        # probably makes sense to remove the UNLICENSED state here.
        return self in [
            LicenseState.TRIAL,
            LicenseState.LICENSED,
            LicenseState.UNLICENSED,
            LicenseState.PENDING_SELECTION,
            LicenseState.PENDING_LICENSE_VERIFICATION,
            LicenseState.PENDING_TRIAL_VERIFICATION,
        ]

    def has_reduced_metric_series_limit(self) -> bool:
        """Returns True if the site should reduce the active metric series limit (typically to 750)."""

        return self is LicenseState.FREE

    def has_remaining_trial_time(self) -> bool:
        """Return True if the site is in a state where remaining trial time exists."""

        return self in [
            LicenseState.TRIAL,
            LicenseState.PENDING_SELECTION,
            LicenseState.PENDING_LICENSE_VERIFICATION,
            LicenseState.PENDING_TRIAL_VERIFICATION,
        ]


class LicenseStateError(Exception):
    pass


@dataclass
class EmailNotification:
    period: timedelta
    remaining_time: timedelta
    subject: str
    message: str


@dataclass
class HeaderNotification:
    roles: Sequence[str]
    subject: str
    message_lines: Sequence[str]

    @property
    def message_html(self) -> str:
        message = "<br><br>".join(self.message_lines)
        return f"<b>{self.subject}</b><br><br>{message}"


@dataclass
class HeaderNotificationSingleLine:
    roles: Sequence[str]
    subject: str
    message: str

    @property
    def message_html(self) -> str:
        if not self.subject:
            return self.message
        return f"<b>{self.subject}</b> {self.message}"


@dataclass
class ActivationBlock:
    subject: str
    message_lines: Sequence[str]

    @property
    def message_raw(self) -> str:
        message = "\n".join(self.message_lines)
        return f"{self.subject}\n{message}"

    @property
    def message_html(self) -> str:
        message = "<br>".join(self.message_lines)
        return f"<b>{self.subject}</b><br>{message}"


@dataclass
class UserEffect:
    header: HeaderNotification | HeaderNotificationSingleLine | None
    email: EmailNotification | None
    block: ActivationBlock | None
    banner: HeaderNotificationSingleLine | None = None


class NotificationHandler(abc.ABC):
    def __init__(self, email_notification: EmailNotification | None) -> None:
        self._email_notification = email_notification

    @abc.abstractmethod
    def manage_notification(self) -> None:
        raise NotImplementedError


class RemainingTrialTime(NamedTuple):
    days: int
    hours: int
    perc: float


class LicensingHandler(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def make(cls) -> LicensingHandler:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def state(self) -> LicenseState:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def message(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def effect_core(self, num_services: int, num_hosts_shadow: int) -> UserEffect:
        raise NotImplementedError

    @abc.abstractmethod
    def effect(self, licensing_settings_link: str | None = None) -> UserEffect:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def notification_handler(self) -> NotificationHandler:
        raise NotImplementedError

    @property
    def remaining_trial_time_rounded(self) -> RemainingTrialTime:
        raise NotImplementedError

    def persist_licensed_state(self, file_path: Path) -> None:
        write_licensed_state(file_path, self.state)


def write_licensed_state(file_path: Path, state: LicenseState) -> None:
    state_repr = 1 if state is LicenseState.LICENSED else 0
    with store.locked(file_path):
        file_path.write_text(str(state_repr))
