#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from types import SimpleNamespace

import pytest

from cmk.gui.crash_reporting import _settings


@pytest.mark.parametrize(
    "email, expected",
    [
        pytest.param("admin@example.com", "admin@example.com", id="address-is-prefilled"),
        pytest.param("cmkadmin", "", id="user-id-fallback-is-not-an-address"),
        pytest.param(None, "", id="unset-email"),
    ],
)
def test_prefilled_contact_email(
    monkeypatch: pytest.MonkeyPatch, email: str | None, expected: str
) -> None:
    """LoggedInUser.email falls back to the user id, which EmailAddress would reject."""
    monkeypatch.setattr(_settings, "user", SimpleNamespace(email=email))
    assert _settings._prefilled_contact_email() == expected
