#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest

from cmk.plugins.kube.schemata import api


@pytest.mark.parametrize(
    "kube_date_time",
    [
        "1970-01-01T00:00:00",
        datetime.datetime(1970, 1, 1, 0, 0, 0),
    ],
)
def test_convert_to_timestamp_raises_error(kube_date_time: str) -> None:
    with pytest.raises(Exception):
        api.convert_to_timestamp(kube_date_time)


@pytest.mark.parametrize(
    "kube_date_time",
    [
        "1970-01-01T00:00:00Z",
        datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.UTC),
    ],
)
def test_convert_to_timestamp_correct_conversion(
    kube_date_time: str,
) -> None:
    assert api.Timestamp(0.0) == api.convert_to_timestamp(kube_date_time)
