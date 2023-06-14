#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from cmk.utils.licensing.handler import (
    LicenseState,
    LicensingHandler,
    NotificationHandler,
    UserEffect,
)


class CRENotificationHandler(NotificationHandler):
    def manage_notification(self) -> None:
        pass


class CRELicensingHandler(LicensingHandler):
    @classmethod
    def make(cls) -> CRELicensingHandler:
        return cls()

    @property
    def state(self) -> LicenseState:
        return LicenseState.LICENSED

    @property
    def message(self) -> str:
        return ""

    def effect_core(self, num_services: int, num_hosts_shadow: int) -> UserEffect:
        return UserEffect(header=None, email=None, block=None)

    def effect(self, licensing_settings_link: str | None = None) -> UserEffect:
        return UserEffect(header=None, email=None, block=None)

    @property
    def notification_handler(self) -> NotificationHandler:
        return CRENotificationHandler(email_notification=None)
