#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Iterator

import pytest
from pytest import MonkeyPatch

import cmk.gui.main
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.session import session

RequestContextFixture = Iterator[None]


@pytest.mark.usefixtures("request_context")
def test_get_start_url_default() -> None:
    assert cmk.gui.main._get_start_url(Config()) == "dashboard.py"


@pytest.mark.usefixtures("request_context")
def test_get_start_url_default_config() -> None:
    config = Config()
    config.start_url = "bla.py"
    assert cmk.gui.main._get_start_url(config) == "bla.py"


@pytest.mark.usefixtures("request_context")
def test_get_start_url_user_config() -> None:
    class MockUser:
        ident = id = "17"  # session wants us to have an id to be able to set it there

        @property
        def start_url(self) -> str:
            return "correct_url.py"

        @property
        def automation_user(self) -> bool:
            return False

    config = Config()
    config.start_url = "wrong_url.py"
    session.user = MockUser()  # type: ignore[assignment]
    assert cmk.gui.main._get_start_url(config) == "correct_url.py"


@pytest.mark.usefixtures("request_context")
def test_get_start_url() -> None:
    start_url = "dashboard.py?name=mein_dashboard"
    request.set_var("start_url", start_url)

    assert cmk.gui.main._get_start_url(Config()) == start_url


@pytest.mark.parametrize(
    "invalid_url",
    [
        "http://localhost/",
        "javascript:alert(1)",
        "javAscRiPt:alert(1)",
        "localhost:80/bla",
    ],
)
@pytest.mark.usefixtures("request_context")
def test_get_start_url_invalid(invalid_url: str) -> None:
    request.set_var("start_url", invalid_url)

    assert cmk.gui.main._get_start_url(Config()) == "dashboard.py"


@pytest.mark.usefixtures("request_context")
def test_get_start_url_invalid_config(monkeypatch: MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "attributes", {"start_url": "http://asdasd/"})
        assert cmk.gui.main._get_start_url(Config()) == "dashboard.py"
