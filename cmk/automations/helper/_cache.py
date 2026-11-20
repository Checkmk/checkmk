#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
from collections.abc import Awaitable
from typing import Final, Self

import redis
from redis.exceptions import RedisError

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
        except RedisError as err:
            raise CacheError("Redis error: Failed to store timestamp of detected change.") from err

    def get_last_detected_change(self) -> float:
        try:
            last = self._client.get(LAST_DETECTED_CHANGE_TOPIC)
            assert not isinstance(last, Awaitable)
            return float(last or 0.0)
        except RedisError as err:
            raise CacheError(
                "Redis error: Failed to retrieve timestamp of last detected change."
            ) from err

    def store_changes_unwatched(self, *, unwatched: bool) -> None:
        """Store whether the watcher may miss changes, e.g. as it cannot watch a new directory."""
        try:
            self._client.set(CHANGES_UNWATCHED_TOPIC, int(unwatched))
        except RedisError as err:
            raise CacheError("Redis error: Failed to store whether changes are unwatched.") from err

    def get_changes_unwatched(self) -> bool | None:
        """Whether the watcher may miss changes, or None if that is not stored, e.g. as Redis has
        restarted since."""
        try:
            unwatched = self._client.get(CHANGES_UNWATCHED_TOPIC)
            assert not isinstance(unwatched, Awaitable)
            return None if unwatched is None else bool(int(unwatched))
        except RedisError as err:
            raise CacheError(
                "Redis error: Failed to retrieve whether changes are unwatched."
            ) from err

    def reload_required(self, last_reload: float) -> bool:
        """Whether a change was detected after *last_reload*, or changes may have gone unnoticed.

        They may also if Redis has lost whether they may, e.g. as it restarted: then it may have
        lost a change, too, until the watcher has restored what it stored.
        """
        try:
            return (
                self.get_changes_unwatched() is not False
                or last_reload < self.get_last_detected_change()
            )
        except CacheError:
            LOGGER.warning("Redis error, assuming reload required")
            return True


class CacheError(Exception): ...
