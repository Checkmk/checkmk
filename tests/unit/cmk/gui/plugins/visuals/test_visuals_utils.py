#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import SiteId

from cmk.gui.plugins.visuals.utils import get_only_sites_from_context


@pytest.mark.parametrize("context,result", [
    pytest.param(
        {"site": "sitename"},
        [SiteId("sitename")],
        id="Single context site enforced",
    ),
    pytest.param(
        {
            "siteopt": {
                "site": ""
            },
        },
        None,
        id="Multiple contexts no site selected",
    ),
    pytest.param(
        {"sites": "first|second"},
        [SiteId("first"), SiteId("second")],
        id="Single context Multiple sites selected",
    ),
    pytest.param(
        {
            "sites": {
                "sites": "first|second"
            },
        },
        [SiteId("first"), SiteId("second")],
        id="Multiple contexts Multiple sites selected",
    ),
])
def test_get_only_sites_from_context(context, result):
    assert get_only_sites_from_context(context) == result
