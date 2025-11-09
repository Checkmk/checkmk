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
        pytest.param("cre", Edition.COMMUNITY, id="legacy-community"),
        pytest.param("cee", Edition.PRO, id="legacy-pro"),
        pytest.param("cce", Edition.ULTIMATE, id="legacy-ultimate"),
        pytest.param("cme", Edition.ULTIMATEMT, id="legacy-ultimatemt"),
        pytest.param("cse", Edition.CLOUD, id="legacy-cloud"),
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
        pytest.param("raw", Edition.COMMUNITY, id="legacy-community"),
        pytest.param("enterprise", Edition.PRO, id="legacy-pro"),
        pytest.param("cloud", Edition.ULTIMATE, id="legacy-ultimate"),
        pytest.param("managed", Edition.ULTIMATEMT, id="legacy-ultimatemt"),
        pytest.param("saas", Edition.CLOUD, id="legacy-cloud"),
    ],
)
def test__edition_from_livestatus_legacy(edition_str: str, expected: Edition) -> None:
    assert _edition_from_livestatus(version_str="2.4.0", edition_str=edition_str) is expected


@pytest.mark.parametrize(
    "version_str",
    [
        pytest.param("2.5.0", id="2.5.0"),
        pytest.param("2.6.0", id="2.6.0"),
        pytest.param("3.0.0", id="3.0.0"),
    ],
)
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
def test__edition_from_livestatus(version_str: str, edition_str: str, expected: Edition) -> None:
    assert _edition_from_livestatus(version_str=version_str, edition_str=edition_str) is expected
