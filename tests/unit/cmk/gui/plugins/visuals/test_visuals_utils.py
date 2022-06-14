#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import SiteId

from cmk.gui.plugins.visuals.utils import get_only_sites_from_context


@pytest.mark.parametrize(
    "context,result",
    [
        pytest.param(
            {"site": {"site": "sitename"}},
            [SiteId("sitename")],
            id="Site enforced",
        ),
        pytest.param(
            {"siteopt": {"site": ""}},
            None,
            id="No site selected",
        ),
        pytest.param(
            {"sites": {"sites": "first|second"}},
            [SiteId("first"), SiteId("second")],
            id="Multiple sites selected",
        ),
    ],
)
def test_get_only_sites_from_context(context, result) -> None:
    assert get_only_sites_from_context(context) == result
