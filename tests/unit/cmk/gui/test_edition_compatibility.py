#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition

from cmk.gui.sites import _edition_from_livestatus
from cmk.gui.watolib.automations import _edition_from_short


@pytest.mark.parametrize(
    "edition, expected",
    [
        pytest.param("cre", Edition.CRE, id="legacy-community"),
        pytest.param("community", Edition.CRE, id="community"),
        pytest.param("cee", Edition.CEE, id="legacy-pro"),
        pytest.param("pro", Edition.CEE, id="pro"),
        pytest.param("cce", Edition.CCE, id="legacy-ultimate"),
        pytest.param("ultimate", Edition.CCE, id="ultimate"),
        pytest.param("cme", Edition.CME, id="legacy-ultimatemt"),
        pytest.param("ultimatemt", Edition.CME, id="ultimatemt"),
        pytest.param("cse", Edition.CSE, id="legacy-cloud"),
        pytest.param("cloud", Edition.CSE, id="cloud"),
    ],
)
def test__edition_from_short(edition: str, expected: Edition) -> None:
    assert _edition_from_short(edition) is expected
    assert _edition_from_livestatus(edition) is expected
