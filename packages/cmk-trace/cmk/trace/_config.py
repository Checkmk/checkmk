#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class LocalTarget:
    port: int


@dataclass
class TraceSendConfig:
    enabled: bool
    target: LocalTarget | str


def service_namespace_from_config(default_namespace: str, config: Mapping[str, str]) -> str:
    """
    >>> service_namespace_from_config("harry", {})
    'harry'
    >>> service_namespace_from_config("harry", {"CONFIG_TRACE_SERVICE_NAMESPACE": "hirsch"})
    'hirsch'
    """
    if namespace := config.get("CONFIG_TRACE_SERVICE_NAMESPACE"):
        return namespace
    return default_namespace


def trace_send_config(config: Mapping[str, str]) -> TraceSendConfig:
    trace_enabled = config.get("CONFIG_TRACE_SEND") == "on"
    if not trace_enabled:
        return TraceSendConfig(enabled=False, target="")

    target: LocalTarget | str
    if (target := config.get("CONFIG_TRACE_SEND_TARGET", "local_site")) == "local_site":
        target = LocalTarget(_trace_receive_port(config))
    return TraceSendConfig(enabled=True, target=target)


def _trace_receive_port(config: Mapping[str, str]) -> int:
    return int(config["CONFIG_TRACE_RECEIVE_PORT"])
