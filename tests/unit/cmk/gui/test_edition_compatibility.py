#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.sites import _edition_from_livestatus
from cmk.gui.watolib.automations import _edition_from_short


@pytest.mark.parametrize(
    "edition_str, expected",
    [
        pytest.param("community", Edition.COMMUNITY, id="community"),
        pytest.param("pro", Edition.PRO, id="pro"),
        pytest.param("ultimate", Edition.ULTIMATE, id="ultimate"),
        pytest.param("ultimatemt", Edition.ULTIMATEMT, id="ultimatemt"),
        pytest.param("cloud", Edition.CLOUD, id="cloud"),
    ],
)
def test__edition_from_short(edition_str: str, expected: Edition) -> None:
    assert _edition_from_short(edition_str) is expected


@pytest.mark.parametrize(
    "edition_str, expected",
    [
        pytest.param("community", Edition.COMMUNITY, id="community"),
        pytest.param("pro", Edition.PRO, id="pro"),
        pytest.param("ultimate", Edition.ULTIMATE, id="ultimate"),
        pytest.param("ultimatemt", Edition.ULTIMATEMT, id="ultimatemt"),
        pytest.param("cloud", Edition.CLOUD, id="cloud"),
        pytest.param("enterprise", None, id="unknown"),
        pytest.param(None, None, id="missing"),
    ],
)
def test__edition_from_livestatus(edition_str: str | None, expected: Edition | None) -> None:
    assert _edition_from_livestatus(edition_str) is expected
