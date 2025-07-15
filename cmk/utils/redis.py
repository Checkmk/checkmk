#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from redis import ConnectionError as RedisConnectionError
from redis import Redis
from redis.client import Pipeline

from cmk.ccc.exceptions import MKTimeout

from cmk.utils.paths import omd_root

QueryData = TypeVar("QueryData")


def get_redis_client() -> Redis[str]:
    """Builds a ready-to-use Redis client instance

    Note: Use the returing object as context manager to ensure proper cleanup.
    """
    if not redis_enabled():
        raise RuntimeError("Redis currently explicitly disabled")
    return Redis.from_url(
        f"unix://{omd_root / 'tmp/run/redis'}",
        db=0,
        encoding="utf-8",
        decode_responses=True,
    )


def redis_server_reachable(client: Redis) -> bool:
    try:
        client.ping()
    except RedisConnectionError:
        return False
    return True


class IntegrityCheckResponse(Enum):
    USE = 1  # Data is up-to-date
    TRY_UPDATE_ELSE_USE = 2  # Try update data if no other process handles it
    UPDATE = 3  # Data requires an update
    UNAVAILABLE = 4  # There is no hope for this cache, abandon


class DataUnavailableException(Exception):
    pass


def query_redis(
    client: Redis[str],
    data_key: str,
    integrity_callback: Callable[[], IntegrityCheckResponse],
    update_callback: Callable[[Pipeline], Any],
    query_callback: Callable[[], QueryData],
    timeout: int | None = None,
    ttl_query_lock: int = 5,
    ttl_update_lock: int = 10,
) -> QueryData:
    query_lock = client.lock(f"{data_key}.query_lock", timeout=ttl_query_lock)
    update_lock = client.lock(f"{data_key}.update_lock", timeout=ttl_update_lock)
    try:
        query_lock.acquire()
        integrity_result = integrity_callback()
        if integrity_result == IntegrityCheckResponse.USE:
            return query_callback()

        if integrity_result == IntegrityCheckResponse.UNAVAILABLE:
            raise DataUnavailableException()

        blocking = integrity_result == IntegrityCheckResponse.UPDATE
        update_lock.acquire(blocking=blocking, blocking_timeout=timeout)
        if update_lock.owned():
            if integrity_callback() == IntegrityCheckResponse.USE:
                return query_callback()
            if query_lock.owned():
                query_lock.release()
            pipeline = client.pipeline()
            update_callback(pipeline)
            query_lock.acquire()
            pipeline.execute()
        elif blocking:
            raise DataUnavailableException("Could not aquire lock in time")
        return query_callback()
    except MKTimeout:
        raise
    except Exception as e:
        raise DataUnavailableException(e) from e
    finally:
        if query_lock.owned():
            query_lock.release()
        if update_lock.owned():
            update_lock.release()


@contextmanager
def disable_redis() -> Iterator[None]:
    last_value = _SWITCH.enabled
    _SWITCH.enabled = False
    try:
        yield
    finally:
        _SWITCH.enabled = last_value


def redis_enabled() -> bool:
    return _SWITCH.enabled


@dataclass
class _ThreadSafeRedisSwitch(threading.local):
    enabled: bool


_SWITCH = _ThreadSafeRedisSwitch(enabled=True)
