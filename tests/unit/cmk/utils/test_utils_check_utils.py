#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.check_utils import unwrap_parameters, wrap_parameters


@pytest.mark.parametrize("params", [
    "foo_levels",
    (1, 2),
    {
        "levels": (1, 2)
    },
])
def test_un_wrap_parameters(params):
    wrapped = wrap_parameters(params)
    assert isinstance(wrapped, dict)
    assert unwrap_parameters(wrapped) == params


def test_noop_wrap_parameters():
    assert {"levels": (1, 2)} == wrap_parameters({"levels": (1, 2)})


def test_noop_unwrap_parameters():
    assert {"levels": (1, 2)} == unwrap_parameters({"levels": (1, 2)})
