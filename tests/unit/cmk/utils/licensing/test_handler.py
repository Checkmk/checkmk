#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.utils.licensing.handler import (
    LicenseState,
    LicensingHandler,
    NotificationHandler,
    RemainingTrialTime,
    UserEffect,
)


class LicensingHandlerMock(LicensingHandler):
    def __init__(self, state: LicenseState) -> None:
        self._state = state

    @property
    def state(self) -> LicenseState:
        return self._state

    @classmethod
    def make(cls) -> LicensingHandler:
        raise NotImplementedError()

    @property
    def message(self) -> str:
        raise NotImplementedError()

    def effect_core(self, num_services: int, num_hosts_shadow: int) -> UserEffect:
        raise NotImplementedError()

    def effect(self, licensing_settings_link: str | None = None) -> UserEffect:
        raise NotImplementedError()

    @property
    def notification_handler(self) -> NotificationHandler:
        raise NotImplementedError()

    @property
    def remaining_trial_time_rounded(self) -> RemainingTrialTime:
        raise NotImplementedError()


@pytest.mark.parametrize(
    "license_state, expected_readable",
    [
        (LicenseState.TRIAL, "trial"),
        (LicenseState.FREE, "free"),
        (LicenseState.LICENSED, "licensed"),
        (LicenseState.UNLICENSED, "unlicensed"),
    ],
)
def test_license_state_readable(license_state: LicenseState, expected_readable: str) -> None:
    assert license_state.readable == expected_readable


@pytest.mark.parametrize(
    "license_state, expected_file_content",
    [
        (LicenseState.TRIAL, "0"),
        (LicenseState.FREE, "0"),
        (LicenseState.LICENSED, "1"),
        (LicenseState.UNLICENSED, "0"),
    ],
)
def test_write_licensed_file(
    tmp_path: Path, license_state: LicenseState, expected_file_content: str
) -> None:
    state_file_path = tmp_path / "licensed_state"
    licensing_handler = LicensingHandlerMock(license_state)
    licensing_handler.persist_licensed_state(state_file_path)
    assert state_file_path.read_text() == expected_file_content
