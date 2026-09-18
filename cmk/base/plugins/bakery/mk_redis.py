#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from shlex import quote
from typing import Literal, TypedDict

from cmk.ccc.exceptions import MKGeneralException

from .bakery_api.v1 import FileGenerator, OS, password_store, Plugin, PluginConfig, register


class ConnectionParamsTcp(TypedDict):
    host: str
    port: int


class ConnectionParamsSocket(TypedDict):
    socket: str


class RedisInstance(TypedDict):
    instance: str
    connection: (
        tuple[Literal["tcp"], ConnectionParamsTcp]
        | tuple[Literal["unix-socket"], ConnectionParamsSocket]
    )
    password: password_store.PasswordId | str | None


RedisConfig = Literal["autodetect"] | tuple[Literal["static"], Sequence[RedisInstance]]


def get_mk_redis_files(conf: RedisConfig) -> FileGenerator:
    yield Plugin(base_os=OS.LINUX, source=Path("mk_redis"))

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mk_redis_config(conf)),
        target=Path("mk_redis.cfg"),
        include_header=True,
    )


def _variable_suffix(instance: str) -> str:
    """The agent plug-in derives the same suffix when it looks the values up.

    Both replace invalid bytes, so a multi-byte character becomes one
    underscore per byte.

    >>> _variable_suffix("My-Fourth-Redis")
    'My_Fourth_Redis'
    >>> _variable_suffix("cache-é")
    'cache___'
    """
    return re.sub(rb"[^A-Za-z0-9_]", b"_", instance.encode()).decode()


def _check_distinct_suffixes(instances: Iterable[str]) -> None:
    seen: dict[str, str] = {}
    for instance in instances:
        suffix = _variable_suffix(instance)
        if suffix in seen:
            raise MKGeneralException(
                f'The Redis instances "{seen[suffix]}" and "{instance}" cannot be told '
                "apart in the agent configuration, where every character that is invalid "
                'in a variable name becomes "_". Please rename one of them.'
            )
        seen[suffix] = instance


def _get_mk_redis_config(conf: RedisConfig) -> Iterator[str]:
    if conf == "autodetect":
        yield "# Autodetect instances"
        return

    _check_distinct_suffixes(e["instance"] for e in conf[1])

    for redis_instance in conf[1]:
        suffix = _variable_suffix(redis_instance["instance"])
        connection = redis_instance["connection"]
        port: str | int
        if connection[0] == "tcp":
            host = connection[1]["host"]
            port = connection[1]["port"]
        else:
            assert connection[0] == "unix-socket"
            host = connection[1]["socket"]
            port = "unix-socket"
        password = redis_instance["password"]

        yield f"REDIS_HOST_{suffix}={quote(host)}"
        yield f"REDIS_PORT_{suffix}={quote(str(port))}"
        if password is not None:
            yield f"REDIS_PASSWORD_{suffix}={quote(password_store.extract(password))}"

    yield "REDIS_INSTANCES=(%s)" % " ".join(quote(e["instance"]) for e in conf[1])


register.bakery_plugin(
    name="mk_redis",
    files_function=get_mk_redis_files,
)
