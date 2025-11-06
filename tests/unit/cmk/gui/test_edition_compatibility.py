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
        pytest.param("cre", Edition.COMMUNITY, id="legacy-community"),
        pytest.param("community", Edition.COMMUNITY, id="community"),
        pytest.param("cee", Edition.PRO, id="legacy-pro"),
        pytest.param("pro", Edition.PRO, id="pro"),
        pytest.param("cce", Edition.ULTIMATE, id="legacy-ultimate"),
        pytest.param("ultimate", Edition.ULTIMATE, id="ultimate"),
        pytest.param("cme", Edition.ULTIMATEMT, id="legacy-ultimatemt"),
        pytest.param("ultimatemt", Edition.ULTIMATEMT, id="ultimatemt"),
        pytest.param("cse", Edition.CLOUD, id="legacy-cloud"),
        pytest.param("cloud", Edition.CLOUD, id="cloud"),
    ],
)
def test__edition_from_short(edition: str, expected: Edition) -> None:
    assert _edition_from_short(edition) is expected
    assert _edition_from_livestatus(edition) is expected
