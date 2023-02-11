#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.licensing.state import is_expired_trial, is_licensed, license_status_message
from cmk.utils.version import Edition


@pytest.fixture(autouse=True)
def _fixture_edition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.utils.licensing.state.edition", lambda: Edition.CRE)


def test_license_status_message() -> None:
    assert license_status_message() == ""


def test_is_licensed() -> None:
    assert is_licensed()


def test_is_expired_trial() -> None:
    assert not is_expired_trial()
