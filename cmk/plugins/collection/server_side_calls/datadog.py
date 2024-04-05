#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    parse_http_proxy,
    replace_macros,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)

from .utils import ProxyType


class Instance(BaseModel):
    api_key: Secret
    app_key: Secret
    api_host: str


class Monitors(BaseModel):
    tags: Sequence[str] = []
    monitor_tags: Sequence[str] = []


class Events(BaseModel):
    max_age: int
    tags: Sequence[str] = []
    tags_to_show: Sequence[str] = []
    syslog_facility: int
    syslog_priority: int
    service_level: int
    add_text: bool


class Logs(BaseModel):
    max_age: int
    query: str
    indexes: Sequence[str]
    syslog_facility: int
    service_level: int
    text: Sequence[tuple[str, str]]


class DatadogParams(BaseModel):
    instance: Instance
    proxy: tuple[ProxyType, str | None] | None = None
    monitors: Monitors | None = None
    events: Events | None = None
    logs: Logs | None = None


def _to_text_args(pairs: Sequence[tuple[str, str]]) -> list[str]:
    return [f"{name}:{key}" for name, key in pairs]


def generate_datadog_command(
    params: DatadogParams, host_config: HostConfig, http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        host_config.name,
        params.instance.api_key,
        params.instance.app_key,
        replace_macros(params.instance.api_host, host_config.macros),
    ]

    if params.proxy is not None:
        args += [
            "--proxy",
            parse_http_proxy(params.proxy, http_proxies),
        ]

    sections = []

    if params.monitors is not None:
        sections.append("monitors")
        args += [
            "--monitor_tags",
            *params.monitors.tags,
            "--monitor_monitor_tags",
            *params.monitors.monitor_tags,
        ]

    if params.events is not None:
        sections.append("events")
        args += [
            "--event_max_age",
            str(params.events.max_age),
            "--event_tags",
            *params.events.tags,
            "--event_tags_show",
            *params.events.tags_to_show,
            "--event_syslog_facility",
            str(params.events.syslog_facility),
            "--event_syslog_priority",
            str(params.events.syslog_priority),
            "--event_service_level",
            str(params.events.service_level),
            *(["--event_add_text"] if params.events.add_text else []),
        ]

    if params.logs is not None:
        sections.append("logs")
        args += [
            "--log_max_age",
            str(params.logs.max_age),
            "--log_query",
            params.logs.query,
            "--log_indexes",
            *params.logs.indexes,
            "--log_text",
            *_to_text_args(params.logs.text),
            "--log_syslog_facility",
            str(params.logs.syslog_facility),
            "--log_service_level",
            str(params.logs.service_level),
        ]

    args += ["--sections"] + sections

    yield SpecialAgentCommand(command_arguments=args)


special_agent_datadog = SpecialAgentConfig(
    name="datadog",
    parameter_parser=DatadogParams.model_validate,
    commands_function=generate_datadog_command,
)
