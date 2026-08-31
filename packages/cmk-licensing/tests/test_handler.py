#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import override

import pytest

from cmk.licensing.handler import (
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
    @override
    def state(self) -> LicenseState:
        return self._state

    @classmethod
    @override
    def make(cls) -> LicensingHandler:
        raise NotImplementedError

    @property
    @override
    def message(self) -> str:
        raise NotImplementedError

    @override
    def effect_core(self, num_services: int, num_hosts_shadow: int) -> UserEffect:
        raise NotImplementedError

    @override
    def effect(self, licensing_settings_link: str | None = None) -> UserEffect:
        raise NotImplementedError

    @property
    @override
    def notification_handler(self) -> NotificationHandler:
        raise NotImplementedError

    @property
    @override
    def remaining_trial_time_rounded(self) -> RemainingTrialTime:
        raise NotImplementedError


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
    "license_state, value",
    [
        (LicenseState.TRIAL, 1),
        (LicenseState.FREE, 2),
        (LicenseState.LICENSED, 3),
        (LicenseState.UNLICENSED, 4),
    ],
)
def test_license_state_stable_value(license_state: LicenseState, value: int) -> None:
    # Since the license states are persisted as their integer values, we need to make sure they
    # never change.
    assert license_state.value == value


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


def test_license_state_properties_trial() -> None:
    assert not LicenseState.TRIAL.blocks_distributed_setup_changes_free()
    assert LicenseState.TRIAL.is_connecting_to_remotes_enabled()
    assert LicenseState.TRIAL.is_adding_as_remote_enabled()
    assert not LicenseState.TRIAL.has_reduced_metric_series_limit()


def test_license_state_properties_free() -> None:
    assert LicenseState.FREE.blocks_distributed_setup_changes_free()
    assert not LicenseState.FREE.is_connecting_to_remotes_enabled()
    assert not LicenseState.FREE.is_adding_as_remote_enabled()
    assert LicenseState.FREE.has_reduced_metric_series_limit()


def test_license_state_properties_licensed() -> None:
    assert not LicenseState.LICENSED.blocks_distributed_setup_changes_free()
    assert LicenseState.LICENSED.is_connecting_to_remotes_enabled()
    assert LicenseState.LICENSED.is_adding_as_remote_enabled()
    assert not LicenseState.LICENSED.has_reduced_metric_series_limit()


def test_license_state_properties_unlicensed() -> None:
    assert not LicenseState.UNLICENSED.blocks_distributed_setup_changes_free()
    assert not LicenseState.UNLICENSED.is_connecting_to_remotes_enabled()
    assert LicenseState.UNLICENSED.is_adding_as_remote_enabled()
    assert not LicenseState.UNLICENSED.has_reduced_metric_series_limit()
