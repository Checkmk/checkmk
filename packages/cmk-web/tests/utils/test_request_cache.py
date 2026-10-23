#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import final

from cmk.web.utils.request_cache import CacheKey, RequestCache


@dataclass(frozen=True)
class _Config:
    start_url: str = "dashboard.py"


@final
class _StartUrl:
    def __init__(self, config: _Config) -> None:
        self.start_url = config.start_url


_KEY = CacheKey("start_url", _StartUrl)


def test_a_value_is_built_from_the_config_of_the_request() -> None:
    assert RequestCache(_Config(start_url="index.py")).get(_KEY).start_url == "index.py"


def test_a_value_is_built_once_per_request() -> None:
    request_cache = RequestCache(_Config())

    assert request_cache.get(_KEY) is request_cache.get(_KEY)


def test_each_request_builds_its_own_value() -> None:
    assert RequestCache(_Config()).get(_KEY) is not RequestCache(_Config()).get(_KEY)
