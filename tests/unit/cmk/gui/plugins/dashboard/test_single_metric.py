#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.gui.plugins.dashboard.single_metric import dashlet_title


@pytest.mark.parametrize(
    "settings, metric_specs, result",
    [
        pytest.param(
            {
                "show_title": False,
                "title": "title",
                "single_infos": ["host", "service"],
            },
            {},
            "",
            id="no show title",
        ),
        pytest.param(
            {
                "show_title": True,
                "single_infos": ["host", "service"],
            },
            {},
            "",
            id="no set title",
        ),
        pytest.param(
            {
                "show_title": True,
                "title": "$SITE$ - $HOST_NAME$ - $SERVICE_DESCRIPTION$",
                "single_infos": ["host", "service"],
            },
            {
                "site": "site",
                "host_name": "host",
                "service_description": "service_description",
            },
            "site - host - service_description",
            id="set title and macros",
        ),
    ],
)
def test_dashlet_title(settings, metric_specs, result):
    assert dashlet_title(settings, metric_specs) == result
