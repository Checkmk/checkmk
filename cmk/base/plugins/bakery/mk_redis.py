#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from shlex import quote
from typing import Literal

from pydantic import BaseModel

from cmk.ccc.exceptions import MKGeneralException

from .bakery_api.v1 import FileGenerator, OS, password_store, Plugin, PluginConfig, register


class _Tcp(BaseModel):
    host: str
    port: int


class _UnixSocket(BaseModel):
    socket: str


class _Instance(BaseModel):
    instance: str
    connection: tuple[Literal["tcp"], _Tcp] | tuple[Literal["unix-socket"], _UnixSocket]
    password: password_store.PasswordId | None = None


RedisConfig = Literal["autodetect"] | tuple[Literal["static"], Sequence[Mapping[str, object]]]


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


def _host_and_port(redis_instance: _Instance) -> tuple[str, str | int]:
    match redis_instance.connection:
        case ("tcp", tcp):
            return tcp.host, tcp.port
        case ("unix-socket", unix_socket):
            return unix_socket.socket, "unix-socket"


def _get_mk_redis_config(conf: RedisConfig) -> Iterator[str]:
    if conf == "autodetect":
        yield "# Autodetect instances"
        return

    yield from _get_static_instances_config([_Instance.model_validate(e) for e in conf[1]])


def _get_static_instances_config(instances: Sequence[_Instance]) -> Iterator[str]:
    _check_distinct_suffixes(i.instance for i in instances)

    for redis_instance in instances:
        suffix = _variable_suffix(redis_instance.instance)
        host, port = _host_and_port(redis_instance)

        yield f"REDIS_HOST_{suffix}={quote(host)}"
        yield f"REDIS_PORT_{suffix}={quote(str(port))}"
        if redis_instance.password is not None:
            yield f"REDIS_PASSWORD_{suffix}={quote(password_store.extract(redis_instance.password))}"

    yield "REDIS_INSTANCES=(%s)" % " ".join(quote(i.instance) for i in instances)


register.bakery_plugin(
    name="mk_redis",
    files_function=get_mk_redis_files,
)
