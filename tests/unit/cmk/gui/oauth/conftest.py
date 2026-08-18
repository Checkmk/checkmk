#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from flask import Flask

from cmk.utils.redis import get_redis_client


@pytest.fixture(name="clean_redis")
def fixture_clean_redis(flask_app: Flask, allow_redis: None) -> None:
    # The fakeredis instance behind get_redis_client() is shared across the
    # test session; start each test from an empty store.
    get_redis_client().flushall()
