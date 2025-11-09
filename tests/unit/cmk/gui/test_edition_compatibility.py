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
        pytest.param("cre", Edition.CRE, id="legacy-community"),
        pytest.param("cee", Edition.CEE, id="legacy-pro"),
        pytest.param("cce", Edition.CCE, id="legacy-ultimate"),
        pytest.param("cme", Edition.CME, id="legacy-ultimatemt"),
        pytest.param("cse", Edition.CSE, id="legacy-cloud"),
        pytest.param("community", Edition.CRE, id="community"),
        pytest.param("pro", Edition.CEE, id="pro"),
        pytest.param("ultimate", Edition.CCE, id="ultimate"),
        pytest.param("ultimatemt", Edition.CME, id="ultimatemt"),
        pytest.param("cloud", Edition.CSE, id="cloud"),
    ],
)
def test__edition_from_short(edition_str: str, expected: Edition) -> None:
    assert _edition_from_short(edition_str) is expected


@pytest.mark.parametrize(
    "version_str",
    [
        pytest.param("2.3.0", id="2.5.0"),
        pytest.param("2.4.0", id="3.0.0"),
    ],
)
@pytest.mark.parametrize(
    "edition_str, expected",
    [
        pytest.param("raw", Edition.CRE, id="legacy-community"),
        pytest.param("enterprise", Edition.CEE, id="legacy-pro"),
        pytest.param("cloud", Edition.CCE, id="legacy-ultimate"),
        pytest.param("managed", Edition.CME, id="legacy-ultimatemt"),
        pytest.param("saas", Edition.CSE, id="legacy-cloud"),
    ],
)
def test__edition_from_livestatus_legacy(
    version_str: str, edition_str: str, expected: Edition
) -> None:
    assert _edition_from_livestatus(version_str=version_str, edition_str=edition_str) is expected


@pytest.mark.parametrize(
    "version_str",
    [
        pytest.param("2.5.0", id="2.5.0"),
        pytest.param("3.0.0", id="3.0.0"),
    ],
)
@pytest.mark.parametrize(
    "edition_str, expected",
    [
        pytest.param("community", Edition.CRE, id="community"),
        pytest.param("pro", Edition.CEE, id="pro"),
        pytest.param("ultimate", Edition.CCE, id="ultimate"),
        pytest.param("ultimatemt", Edition.CME, id="ultimatemt"),
        pytest.param("cloud", Edition.CSE, id="cloud"),
    ],
)
def test__edition_from_livestatus(version_str: str, edition_str: str, expected: Edition) -> None:
    assert _edition_from_livestatus(version_str=version_str, edition_str=edition_str) is expected
