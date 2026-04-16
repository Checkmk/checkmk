#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
import time
from zoneinfo import ZoneInfo

import time_machine

from cmk.checkengine.discovery._autodiscovery import _may_rediscover
from cmk.checkengine.discovery._filters import RediscoveryParameters


def test_may_rediscover_relies_on_time_zone_when_disallowing() -> None:
    rediscovery_parameters = RediscoveryParameters(
        {"excluded_time": [((9, 15), (9, 45))], "group_time": 3600},
    )

    with time_machine.travel(
        datetime.datetime(2026, 1, 6, 9, 30, tzinfo=ZoneInfo("Europe/Berlin")),
        tick=False,
    ):
        assert (
            _may_rediscover(
                rediscovery_parameters=rediscovery_parameters,
                reference_time=time.mktime(time.localtime()),
                oldest_queued=0.0,
            )
            == "we are currently in a disallowed time of day"
        )


def test_may_rediscover_relies_on_time_zone_when_allowing() -> None:
    rediscovery_parameters = RediscoveryParameters(
        {"excluded_time": [((9, 15), (9, 45))], "group_time": 3600},
    )

    with time_machine.travel(
        datetime.datetime(2026, 1, 6, 10, 30, tzinfo=ZoneInfo("Europe/Berlin")),
        tick=False,
    ):
        assert (
            _may_rediscover(
                rediscovery_parameters=rediscovery_parameters,
                reference_time=time.mktime(time.localtime()),
                oldest_queued=0.0,
            )
            == ""
        )
