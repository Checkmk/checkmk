#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
from collections.abc import Awaitable
from typing import Final, Self

import redis
from redis.exceptions import ConnectionError  # noqa: A004

LAST_DETECTED_CHANGE_TOPIC: Final = "last_change_detected"
CHANGES_UNWATCHED_TOPIC: Final = "changes_unwatched"
LOGGER = logging.getLogger(__name__)


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
            raise CacheError(
                "Redis unavailable: Failed to store timestamp of detected change."
            ) from err

    def get_last_detected_change(self) -> float:
        try:
            last = self._client.get(LAST_DETECTED_CHANGE_TOPIC)
            assert not isinstance(last, Awaitable)
            return float(last or 0.0)
        except ConnectionError as err:
            raise CacheError(
                "Redis unavailable: Failed to retrieve timestamp of last detected change."
            ) from err

    def store_changes_unwatched(self, *, unwatched: bool) -> None:
        """Store whether the watcher may miss changes, e.g. as it cannot watch a new directory."""
        try:
            self._client.set(CHANGES_UNWATCHED_TOPIC, int(unwatched))
        except ConnectionError as err:
            raise CacheError(
                "Redis unavailable: Failed to store whether changes are unwatched."
            ) from err

    def _changes_unwatched(self) -> bool:
        try:
            unwatched = self._client.get(CHANGES_UNWATCHED_TOPIC)
            assert not isinstance(unwatched, Awaitable)
            return bool(int(unwatched or 0))
        except ConnectionError as err:
            raise CacheError(
                "Redis unavailable: Failed to retrieve whether changes are unwatched."
            ) from err

    def reload_required(self, last_reload: float) -> bool:
        """Whether a change was detected after *last_reload*, or changes may have gone unnoticed."""
        try:
            return self._changes_unwatched() or last_reload < self.get_last_detected_change()
        except CacheError:
            LOGGER.warning("Redis unavailable, assuming reload required")
            return True


class CacheError(Exception): ...
