#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Final, Self

import redis

LAST_AUTOMATION_HELPER_RELOAD_TOPIC: Final = "last_automation_helper_reload"


@dataclasses.dataclass(frozen=True)
class Cache:
    _client: redis.Redis

    @classmethod
    def setup(cls, *, client: redis.Redis) -> Self:
        return cls(_client=client)

    def clear(self) -> None:
        self._client.delete(LAST_AUTOMATION_HELPER_RELOAD_TOPIC)

    def store_last_automation_helper_reload(self, time: float) -> None:
        self._client.set(LAST_AUTOMATION_HELPER_RELOAD_TOPIC, time)

    @property
    def last_automation_helper_reload(self) -> float:
        if fetched_value := self._client.get(LAST_AUTOMATION_HELPER_RELOAD_TOPIC):
            return float(fetched_value)
        return 0.0
