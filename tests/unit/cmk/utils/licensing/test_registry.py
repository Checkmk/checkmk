#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.licensing.registry import (
    get_license_message,
    is_licensed,
    register_cre_licensing_handler,
)
from cmk.utils.version import Edition


@pytest.fixture(autouse=True)
def _fixture_edition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.utils.licensing.registry.edition", lambda: Edition.CRE)


@pytest.fixture(autouse=True)
def _fixture_register_handler() -> None:
    register_cre_licensing_handler()


def test_license_status_message() -> None:
    assert get_license_message() == ""


def test_is_licensed() -> None:
    assert is_licensed()
