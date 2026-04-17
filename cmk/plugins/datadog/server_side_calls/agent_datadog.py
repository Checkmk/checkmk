#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

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


def _to_text_args(pairs: Sequence[dict[str, str]]) -> list[str]:
    return [f"{pair['name']}:{pair['key']}" for pair in pairs]


class Instance(BaseModel):
    api_key: Secret
    app_key: Secret
    api_host: str


class Monitors(BaseModel):
    tags: list[str] = Field(default_factory=list)
    monitor_tags: list[str] = Field(default_factory=list)


class Events(BaseModel):
    max_age: float
    tags: list[str] = Field(default_factory=list)
    tags_to_show: list[str] = Field(default_factory=list)
    syslog_facility: tuple[str, int]
    syslog_priority: tuple[str, int]
    service_level: tuple[str, int]
    add_text: str


class LogsConfig(BaseModel):
    max_age: float
    query: str
    indexes: list[str]
    text: list[dict[str, str]] = Field(default_factory=list)
    syslog_facility: tuple[str, int]
    service_level: tuple[str, int]


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
        "--apikey-id",
        params.instance.api_key,
        "--appkey-id",
        params.instance.app_key,
        host_config.name,
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
        for tag in params.monitors.tags:
            args += ["--monitor_tag", tag]
        for tag in params.monitors.monitor_tags:
            args += ["--monitor_monitor_tag", tag]
    if params.events:
        sections.append("events")
        args += [
            "--event_max_age",
            str(int(params.events.max_age)),
        ]
        for tag in params.events.tags:
            args += ["--event_tag", tag]
        for tag in params.events.tags_to_show:
            args += ["--event_tag_show", tag]
        args += [
            "--event_syslog_facility",
            str(params.events.syslog_facility[1]),
            "--event_syslog_priority",
            str(params.events.syslog_priority[1]),
            "--event_service_level",
            str(params.events.service_level[1]),
            *(["--event_add_text"] if params.events.add_text == "add_text" else []),
        ]

    if params.logs:
        sections.append("logs")
        args += [
            "--log_max_age",
            str(int(params.logs.max_age)),
            "--log_query",
            params.logs.query,
        ]
        for idx in params.logs.indexes:
            args += ["--log_index", idx]
        for text_arg in _to_text_args(params.logs.text):
            args += ["--log_text_element", text_arg]
        args += [
            "--log_syslog_facility",
            str(params.logs.syslog_facility[1]),
            "--log_service_level",
            str(params.logs.service_level[1]),
        ]
    for section in sections:
        args += ["--section", section]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_datadog = SpecialAgentConfig(
    name="datadog",
    parameter_parser=Params.model_validate,
    commands_function=agent_datadog_arguments,
)
