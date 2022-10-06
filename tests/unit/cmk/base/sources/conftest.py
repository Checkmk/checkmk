#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.core_helpers.cache import FileCacheGlobals


@pytest.fixture(autouse=True)
def reset_mutable_global_state():
    def reset(cls, attr, value):
        # Make sure we are not *adding* any field.
        assert hasattr(cls, attr)
        setattr(cls, attr, value)

    yield
    reset(FileCacheGlobals, "disabled", False)
    reset(FileCacheGlobals, "maybe", False)
    reset(FileCacheGlobals, "use_outdated", False)
    reset(FileCacheGlobals, "keep_outdated", False)
    reset(FileCacheGlobals, "tcp_use_only_cache", False)
