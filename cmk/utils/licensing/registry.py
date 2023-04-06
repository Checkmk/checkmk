#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Type

from cmk.utils.licensing.cre_handler import CRELicensingHandler
from cmk.utils.licensing.handler import (
    LicenseState,
    LicenseStateError,
    LicensingHandler,
    NotificationHandler,
    RemainingTrialTime,
    UserEffect,
)
from cmk.utils.version import Edition, edition


class LicensingHandlerRegistry:
    def __init__(self) -> None:
        self._entries: dict[Edition, Type[LicensingHandler]] = {}

    def register(
        self,
        *,
        cmk_edition: Edition,
        licensing_handler: Type[LicensingHandler],
    ) -> None:
        self._entries[cmk_edition] = licensing_handler

    def __getitem__(self, key: Edition) -> Type[LicensingHandler]:
        return self._entries.__getitem__(key)


licensing_handler_registry = LicensingHandlerRegistry()


def _get_licensing_handler() -> Type[LicensingHandler]:
    return licensing_handler_registry[edition()]


def _make_licensing_handler() -> LicensingHandler:
    return _get_licensing_handler().make()


def is_free() -> bool:
    return _make_licensing_handler().state is LicenseState.FREE


def is_trial() -> bool:
    return _make_licensing_handler().state is LicenseState.TRIAL


def is_licensed() -> bool:
    return _make_licensing_handler().state is LicenseState.LICENSED


def is_unlicensed() -> bool:
    return _make_licensing_handler().state is LicenseState.UNLICENSED


def get_license_message() -> str:
    return _make_licensing_handler().message


def get_remaining_trial_time() -> RemainingTrialTime:
    handler = _make_licensing_handler()
    if handler.state is LicenseState.TRIAL:
        return handler.remaining_trial_time
    raise LicenseStateError(
        "Remaining trial time requested for non trial license state: %s" % str(handler.state)
    )


def get_licensing_user_effect_core(num_services: int, num_hosts_shadow: int) -> UserEffect:
    return _make_licensing_handler().effect_core(num_services, num_hosts_shadow)


def get_licensing_user_effect(licensing_settings_link: str | None = None) -> UserEffect:
    return _make_licensing_handler().effect(licensing_settings_link)


def get_licensing_notification_handler() -> NotificationHandler:
    return _make_licensing_handler().notification_handler


def register_cre_licensing_handler():
    # There is no license management planned for the CRE -> Always licensed
    licensing_handler_registry.register(
        cmk_edition=Edition.CRE,
        licensing_handler=CRELicensingHandler,
    )
