#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator, Sequence

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    EnvProxy,
    HostConfig,
    NoProxy,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    URLProxy,
)


def _to_text_args(pairs: Sequence[tuple[str, str]]) -> list[str]:
    return [f"{name}:{key}" for name, key in pairs]


class Instance(BaseModel):
    api_key: Secret
    app_key: Secret
    api_host: str


class Monitors(BaseModel):
    tags: list[str] = Field(default_factory=list)
    monitor_tags: list[str] = Field(default_factory=list)


class Events(BaseModel):
    max_age: int
    tags: list[str] = Field(default_factory=list)
    tags_to_show: list[str] = Field(default_factory=list)
    syslog_facility: int
    syslog_priority: int
    service_level: int
    add_text: bool


class LogsConfig(BaseModel):
    max_age: int
    query: str
    indexes: list[str]
    text: list[tuple[str, str]] = Field(default_factory=list)
    syslog_facility: int
    service_level: int


class Params(BaseModel):
    instance: Instance
    proxy: URLProxy | NoProxy | EnvProxy | None = None
    monitors: Monitors | None = None
    events: Events | None = None
    logs: LogsConfig | None = None


def agent_datadog_arguments(
    params: Params,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        host_config.name,
        params.instance.api_key.unsafe(),
        params.instance.app_key.unsafe(),
        params.instance.api_host,
    ]

    match params.proxy:
        case URLProxy(url=url):
            args += ["--proxy", url]
        case EnvProxy():
            args += ["--proxy", "FROM_ENVIRONMENT"]
        case NoProxy():
            args += ["--proxy", "NO_PROXY"]

    sections = []
    if params.monitors:
        sections.append("monitors")
        args += [
            "--monitor_tags",
            *params.monitors.tags,
            "--monitor_monitor_tags",
            *params.monitors.monitor_tags,
        ]
    if params.events:
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

    if params.logs:
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
    parameter_parser=Params.model_validate,
    commands_function=agent_datadog_arguments,
)
