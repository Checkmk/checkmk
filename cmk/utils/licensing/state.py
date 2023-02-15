#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Care for the licensing state of a Checkmk installation"""

import enum
from typing import Callable, NamedTuple

from cmk.utils.version import edition, Edition


class LicenseState(enum.Enum):
    """All possible license states of the Checkmk site"""

    TRIAL = enum.auto()
    FREE = enum.auto()
    LICENSED = enum.auto()
    EXPIRED = enum.auto()


class _Handlers(NamedTuple):
    status: Callable[[], LicenseState]
    message: Callable[[], str]


class GetLicenseStateRegistry:
    def __init__(self) -> None:
        self._entries: dict[Edition, _Handlers] = {}

    def register(
        self,
        cmk_edition: Edition,
        *,
        status_handler: Callable[[], LicenseState],
        message_handler: Callable[[], str],
    ) -> None:
        self._entries[cmk_edition] = _Handlers(status=status_handler, message=message_handler)

    def __getitem__(self, key: Edition) -> _Handlers:
        return self._entries.__getitem__(key)


get_license_state_registry = GetLicenseStateRegistry()


def license_status_message() -> str:
    return get_license_state_registry[edition()].message()


def _get_license_status() -> LicenseState:
    return get_license_state_registry[edition()].status()


def is_trial() -> bool:
    return _get_license_status() is LicenseState.TRIAL


def is_licensed() -> bool:
    return _get_license_status() is LicenseState.LICENSED


def is_expired_trial() -> bool:
    return _get_license_status() is LicenseState.FREE


def register_get_license_state():
    # There is no license management planned for the CRE -> Always licensed
    get_license_state_registry.register(
        Edition.CRE,
        status_handler=lambda: LicenseState.LICENSED,
        message_handler=lambda: "",
    )
