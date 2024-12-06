#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Final, Self

import redis

LAST_DETECTED_CHANGE_TOPIC: Final = "last_change_detected"
LAST_AUTOMATION_HELPER_RELOAD_TOPIC: Final = "last_automation_helper_reload"


@dataclasses.dataclass(frozen=True)
class Cache:
    _client: redis.Redis

    @classmethod
    def setup(cls, *, client: redis.Redis) -> Self:
        return cls(_client=client)

    def clear(self) -> None:
        self._client.delete(LAST_AUTOMATION_HELPER_RELOAD_TOPIC)

    def store_last_automation_helper_reload(self, worker_id: str, time: float) -> None:
        self._client.hset(
            LAST_AUTOMATION_HELPER_RELOAD_TOPIC,
            key=worker_id,
            value=time,
        )

    def store_last_detected_change(self, time: float) -> None:
        self._client.set(LAST_DETECTED_CHANGE_TOPIC, time)

    def last_automation_helper_reload(self, worker_id: str) -> float:
        return float(self._client.hget(LAST_AUTOMATION_HELPER_RELOAD_TOPIC, key=worker_id) or 0.0)

    @property
    def last_detected_change(self) -> float:
        return float(self._client.get(LAST_DETECTED_CHANGE_TOPIC) or 0.0)

    def reload_required(self, worker_id: str) -> bool:
        return self.last_automation_helper_reload(worker_id) < self.last_detected_change
