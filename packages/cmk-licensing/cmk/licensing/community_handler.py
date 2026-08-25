#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import override

from cmk.licensing.handler import (
    LicenseState,
    LicensingHandler,
    NotificationHandler,
    UserEffect,
)


class CommunityNotificationHandler(NotificationHandler):
    @override
    def manage_notification(self) -> None:
        pass


class CommunityLicensingHandler(LicensingHandler):
    @classmethod
    @override
    def make(cls) -> CommunityLicensingHandler:
        return cls()

    @property
    @override
    def state(self) -> LicenseState:
        return LicenseState.LICENSED

    @property
    @override
    def message(self) -> str:
        return ""

    @override
    def effect_core(self, num_services: int, num_hosts_shadow: int) -> UserEffect:
        return UserEffect(header=None, email=None, block=None)

    @override
    def effect(self, licensing_settings_link: str | None = None) -> UserEffect:
        return UserEffect(header=None, email=None, block=None)

    @property
    @override
    def notification_handler(self) -> NotificationHandler:
        return CommunityNotificationHandler(email_notification=None)
