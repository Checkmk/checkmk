#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

from cmk.ccc.version import Edition, edition
from cmk.licensing.basics.features import FeatureName, licensed_features
from cmk.licensing.community_handler import CommunityLicensingHandler
from cmk.licensing.handler import (
    LicenseState,
    LicenseStateError,
    LicensingHandler,
    NotificationHandler,
    RemainingTrialTime,
    UserEffect,
)


class LicensingHandlerRegistry:
    def __init__(self) -> None:
        self._entries: dict[Edition, Callable[[], LicensingHandler]] = {}

    def register(
        self,
        *,
        cmk_edition: Edition,
        licensing_handler_factory: Callable[[], LicensingHandler],
    ) -> None:
        self._entries[cmk_edition] = licensing_handler_factory

    def __getitem__(self, key: Edition) -> Callable[[], LicensingHandler]:
        return self._entries.__getitem__(key)


# TODO remove registry and directly pass handlers
licensing_handler_registry = LicensingHandlerRegistry()


def _get_licensing_handler_factory(omd_root: Path) -> Callable[[], LicensingHandler]:
    return licensing_handler_registry[edition(omd_root)]


def _make_licensing_handler(omd_root: Path) -> LicensingHandler:
    return _get_licensing_handler_factory(omd_root)()


def is_free(omd_root: Path) -> bool:
    return _make_licensing_handler(omd_root).state is LicenseState.FREE


def is_trial(omd_root: Path) -> bool:
    return _make_licensing_handler(omd_root).state is LicenseState.TRIAL


def is_licensed(omd_root: Path) -> bool:
    return _make_licensing_handler(omd_root).state is LicenseState.LICENSED


def is_unlicensed(omd_root: Path) -> bool:
    return _make_licensing_handler(omd_root).state is LicenseState.UNLICENSED


def get_license_message(omd_root: Path) -> str:
    return _make_licensing_handler(omd_root).message


def get_license_state(omd_root: Path) -> LicenseState:
    return _make_licensing_handler(omd_root).state


def get_remaining_trial_time_rounded(omd_root: Path) -> RemainingTrialTime:
    handler = _make_licensing_handler(omd_root)
    if handler.state is LicenseState.TRIAL:
        return handler.remaining_trial_time_rounded
    raise LicenseStateError(
        "Remaining trial time requested for non trial license state: %s" % str(handler.state)
    )


def get_licensing_user_effect_core(
    omd_root: Path, num_services: int, num_hosts_shadow: int
) -> UserEffect:
    return _make_licensing_handler(omd_root).effect_core(num_services, num_hosts_shadow)


def get_licensing_user_effect(
    omd_root: Path, licensing_settings_link: str | None = None
) -> UserEffect:
    return _make_licensing_handler(omd_root).effect(licensing_settings_link)


def get_licensing_notification_handler(omd_root: Path) -> NotificationHandler:
    return _make_licensing_handler(omd_root).notification_handler


def is_feature_enabled(omd_root: Path, feature: FeatureName) -> bool:
    return licensed_features(omd_root, edition(omd_root)).get_flag(feature).enabled


def register_community_licensing_handler() -> None:
    # There is no license management planned for Checkmk Community -> Always licensed
    licensing_handler_registry.register(
        cmk_edition=Edition.COMMUNITY,
        licensing_handler_factory=CommunityLicensingHandler.make,
    )
