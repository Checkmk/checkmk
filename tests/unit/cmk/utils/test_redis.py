#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.redis import get_redis_client


class TestCheckmkRedisClient:
    def test_initialization_decode_activated(self):
        assert get_redis_client().connection_pool.connection_kwargs.get(
            "decode_responses",
            False,
        )
