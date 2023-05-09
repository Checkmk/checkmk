#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base import events


@pytest.mark.parametrize("context,expected", [
    ("", {}),
    ("TEST=test", {
        "TEST": "test"
    }),
    ("SERVICEOUTPUT=with_light_vertical_bar_\u2758", {
        "SERVICEOUTPUT": "with_light_vertical_bar_|"
    }),
    ("LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758", {
        "LONGSERVICEOUTPUT": "with_light_vertical_bar_|"
    }),
    ("NOT_INFOTEXT=with_light_vertical_bar_\u2758", {
        "NOT_INFOTEXT": "with_light_vertical_bar_\u2758"
    }),
])
def test_raw_context_from_string(context, expected):
    assert events.raw_context_from_string(context) == expected
