#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from fakeredis import FakeRedis

from cmk.automations.helper._cache import Cache


@pytest.fixture(name="cache")
def get_cache() -> Cache:
    """A cache as the watcher prepares it when it starts, before the workers do."""
    cache = Cache.setup(client=FakeRedis())
    cache.store_changes_unwatched(unwatched=False)
    return cache
