#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable

import pytest

import livestatus

from cmk.utils.licensing.state import (
    get_license_status,
    is_expired_trial,
    is_licensed,
    license_status_message,
    LicenseState,
)
from cmk.utils.version import Edition


@pytest.fixture(name="non_free_edition")
def fixture_non_free_edition(
    edition: Edition, monkeypatch: pytest.MonkeyPatch
) -> Iterable[Edition]:
    if edition is Edition.CRE:
        pytest.skip("Test is only relevant for non-CRE editions")
    monkeypatch.setattr("cmk.utils.licensing.state.is_raw_edition", lambda: False)
    yield edition


def test_raw_edition_is_always_licensed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.utils.licensing.state.is_raw_edition", lambda: True)
    assert is_expired_trial() is False
    assert is_licensed() is True
    assert get_license_status() is LicenseState.LICENSED
    assert license_status_message() == ""


@pytest.mark.usefixtures("non_free_edition")
def test_fallback_to_free_on_livestatus_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_exc(q: str) -> livestatus.LivestatusResponse:
        raise livestatus.MKLivestatusSocketError("No livestatus, sorry!")

    monkeypatch.setattr("cmk.utils.licensing.state._query", raise_exc)
    assert is_expired_trial() is True
    assert is_licensed() is False
    assert get_license_status() is LicenseState.FREE


@pytest.mark.usefixtures("non_free_edition")
def test_nonfree_editions_in_trial_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.utils.licensing.state._get_expired_status", lambda: LicenseState.TRIAL)
    assert is_expired_trial() is False
    assert is_licensed() is False
    assert get_license_status() is LicenseState.TRIAL


@pytest.mark.usefixtures("non_free_edition")
def test_nonfree_editions_in_free_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.utils.licensing.state._get_expired_status", lambda: LicenseState.FREE)
    assert is_expired_trial() is True
    assert is_licensed() is False
    assert get_license_status() is LicenseState.FREE


@pytest.mark.usefixtures("non_free_edition")
def test_license_status_message_nonfree_editions_trial_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.utils.licensing.state._get_expired_status", lambda: LicenseState.TRIAL)
    monkeypatch.setattr("cmk.utils.licensing.state._get_age_trial", lambda: 31 * 24 * 60 * 60)

    assert license_status_message() == "Trial expired"


@pytest.mark.usefixtures("non_free_edition")
def test_license_status_message_nonfree_editions_trial_expires_in_2_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.utils.licensing.state._get_expired_status", lambda: LicenseState.TRIAL)
    monkeypatch.setattr("cmk.utils.licensing.state._get_age_trial", lambda: 28 * 24 * 60 * 60)

    assert license_status_message() == "Trial expires in 2 days"


@pytest.mark.usefixtures("non_free_edition")
def test_license_status_message_nonfree_editions_trial_expires_today(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.utils.licensing.state._get_expired_status", lambda: LicenseState.TRIAL)
    monkeypatch.setattr("cmk.utils.licensing.state._get_age_trial", lambda: 30 * 24 * 60 * 60)

    assert license_status_message().startswith("Trial expires today")


@pytest.mark.usefixtures("non_free_edition")
def test_license_status_message_nonfree_editions_is_licensed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.utils.licensing.state.is_licensed", lambda: True)

    assert license_status_message().startswith("Licensed")
