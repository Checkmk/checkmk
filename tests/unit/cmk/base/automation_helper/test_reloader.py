#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from pytest_mock import MockerFixture

from cmk.base.automation_helper._cache import Cache
from cmk.base.automation_helper._config import ReloaderConfig
from cmk.base.automation_helper._reloader import run


def test_reloader(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_callback = mocker.MagicMock()
    reloader_config = ReloaderConfig(
        active=True,
        poll_interval=0.01,
        aggregation_interval=0.0,
    )
    with run(
        reloader_config,
        cache,
        mock_reload_callback,
    ):
        cache.store_last_detected_change(1)
        time.sleep(2 * reloader_config.poll_interval)
    mock_reload_callback.assert_called_once()
