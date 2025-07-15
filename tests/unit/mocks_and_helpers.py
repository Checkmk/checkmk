#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from tests.testlib.common.repo import repo_path

import cmk.ccc.debug

import cmk.utils.caching
import cmk.utils.paths
from cmk.utils.licensing.handler import (
    LicenseState,
    LicensingHandler,
    NotificationHandler,
    UserEffect,
)

import cmk.crypto.password_hashing
from cmk.agent_based.legacy import discover_legacy_checks, FileLoader, find_plugin_files


class FixPluginLegacy:
    """Access legacy dicts like `check_info`"""

    def __init__(self) -> None:
        result = discover_legacy_checks(
            find_plugin_files(repo_path() / "cmk/base/legacy_checks"),
            FileLoader(
                precomile_path=cmk.utils.paths.precompiled_checks_dir,
                makedirs=lambda path: Path(path).mkdir(mode=0o770, exist_ok=True, parents=True),
            ),
            raise_errors=True,
        )
        self.check_info = {p.name: p for p in result.sane_check_info}


class DummyNotificationHandler(NotificationHandler):
    def manage_notification(self) -> None:
        pass


class DummyLicensingHandler(LicensingHandler):
    @classmethod
    def make(cls) -> "DummyLicensingHandler":
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
        return DummyNotificationHandler(email_notification=None)
