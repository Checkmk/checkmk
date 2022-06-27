#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest

from cmk.special_agents.utils_kubernetes.transform import convert_to_timestamp


@pytest.mark.parametrize(
    "kube_date_time",
    [
        "1970-01-01T00:00:00",
        datetime.datetime(1970, 1, 1, 0, 0, 0),
    ],
)
def test_convert_to_timestamp_raises_error(kube_date_time) -> None:
    with pytest.raises(Exception):
        convert_to_timestamp(kube_date_time)


@pytest.mark.parametrize(
    "kube_date_time",
    [
        "1970-01-01T00:00:00Z",
        datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
    ],
)
def test_convert_to_timestamp_correct_conversion(kube_date_time) -> None:
    assert 0 == convert_to_timestamp(kube_date_time)
