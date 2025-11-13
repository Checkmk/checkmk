#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
import uuid
from collections.abc import Callable, Hashable
from typing import Final, TypedDict

from cmk.server_side_programs.v1_unstable import Storage

# A namespace to match a string to a uuid hash.
_HASH_NAMESPACE: Final = uuid.UUID("be8bc5b5-a401-4acc-b8db-a875cca98c79")
# A sentinel for separating args from kwargs.
_KWARG_MARK: Final = object()


def cache_ttl[**P, R](store: Storage, *, ttl: int) -> Callable[[Callable[P, R]], Callable[P, R]]:
    if ttl < 0:
        raise ValueError("Time to live value must be a positive integer.")

    class Cache[T](TypedDict):
        ts: float
        data: T

    def decorator(f: Callable[P, R]) -> Callable[P, R]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if ttl == 0:
                return f(*args, **kwargs)

            if any(not isinstance(arg, Hashable) for arg in args):
                raise ValueError(f"Unhashable arg values: {args}")
            if any(not isinstance(kv, Hashable) for kv in kwargs.values()):
                raise ValueError(f"Unhashable kwarg values: {kwargs}")

            # generate a unique key hash based on the passed arguments.
            key = _hash(str(args + (_KWARG_MARK,) + tuple(sorted(kwargs.items()))))

            if (data := store.read(key, None)) is not None:
                raw_cache = json.loads(data)
                cache = Cache[R](ts=raw_cache["ts"], data=raw_cache["data"])

                if 0 < time.time() - cache["ts"] < ttl:
                    return cache["data"]

            new_data = f(*args, **kwargs)
            new_cache = Cache[R](ts=time.time(), data=new_data)
            store.write(key, json.dumps(new_cache))

            return new_data

        return wrapper

    return decorator


def _hash(value: str) -> str:
    return uuid.uuid5(_HASH_NAMESPACE, value).hex
