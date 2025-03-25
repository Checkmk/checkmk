#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Final, Self

import redis
from redis.exceptions import ConnectionError

LAST_DETECTED_CHANGE_TOPIC: Final = "last_change_detected"


@dataclasses.dataclass(frozen=True)
class Cache:
    _client: redis.Redis

    @classmethod
    def setup(cls, *, client: redis.Redis) -> Self:
        return cls(_client=client)

    def store_last_detected_change(self, time: float) -> None:
        try:
            self._client.set(LAST_DETECTED_CHANGE_TOPIC, time)
        except ConnectionError as err:
            raise CacheError("Failed to store timestamp of detected change.") from err

    def get_last_detected_change(self) -> float:
        try:
            return float(self._client.get(LAST_DETECTED_CHANGE_TOPIC) or 0.0)
        except ConnectionError as err:
            raise CacheError("Failed to retrieve timestamp of last detected change.") from err

    def reload_required(self, last_reload: float) -> bool:
        return last_reload < self.get_last_detected_change()


class CacheError(Exception): ...
