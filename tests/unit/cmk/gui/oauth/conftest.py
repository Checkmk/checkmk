#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest
from flask import Flask

from cmk.gui import oauth
from cmk.utils.redis import get_redis_client


@pytest.fixture(name="clean_redis")
def fixture_clean_redis(flask_app: Flask, allow_redis: None) -> None:
    # The fakeredis instance behind get_redis_client() is shared across the
    # test session; start each test from an empty store.
    get_redis_client().flushall()


@pytest.fixture(name="cleanup_registered_clients")
def fixture_cleanup_registered_clients() -> Iterator[None]:
    # client_store()'s connection is a shared, process-wide singleton -- clients
    # registered here would otherwise outlive the test and leak into every test
    # that runs afterwards in the same pytest session.
    yield
    store = oauth.client_store()
    store.delete([registration.client_id for registration in store.list()])
