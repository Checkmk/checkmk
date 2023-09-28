#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.urls import is_allowed_url


@pytest.mark.parametrize(
    "url,expected",
    [
        pytest.param(
            "view.py?view_name=service&host=stable&service=APT Updates&site=stable",
            True,
            id="Link to service",
        ),
    ],
)
def test_is_allowed_url_regression(url: str, expected: bool) -> None:
    """Test for allowed urls

    is_allowed_url has also several doctests
    Reasons for this test:
        - Werk 13197
    """
    assert is_allowed_url(url) == expected
