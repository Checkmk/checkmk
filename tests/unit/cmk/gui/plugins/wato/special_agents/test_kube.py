#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.special_agents import kube


@pytest.mark.parametrize(
    "url",
    [
        "localhost",  # GUI transforms this to 'http://localhost', so users don't see this
        "http://",
        "https://?example:8080/",
        "http://::1",
        "http://localhost!:8080",
        "http://:8080",
    ],
)
def test__validate_reject(url: str) -> None:
    with pytest.raises(MKUserError):
        kube._url(title="", default_value="https://", _help="")._validate_value(url, "varprefix")
        kube._validate(url, "varprefix")


@pytest.mark.parametrize(
    "url",
    [
        "https://a?example:8080/",
        "https://example.com",
        "https://[::1]/",
        "http://[0:0:0:0:0:0:0:1]",
        "http://localhost",
        "https://localhost:8080",
        "https://123:8080",
        "https://127.0.0.1:8080",
        "https://127.0.0.1:8080/",
        "https://127.0.0.1:8080//",
    ],
)
def test__validate_accept(url: str) -> None:
    kube._url(title="", default_value="https://", _help="")._validate_value(url, "varprefix")
    kube._validate(url, "varprefix")
