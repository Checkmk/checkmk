#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TYPE_CHECKING
from redis import Redis
from .paths import omd_root

# See tests/typeshed/redis
if TYPE_CHECKING:
    RedisDecoded = Redis[str]


def get_redis_client() -> 'RedisDecoded':
    return Redis.from_url(
        f"unix://{omd_root}/tmp/run/redis",
        db=0,
        encoding="utf-8",
        decode_responses=True,
    )
