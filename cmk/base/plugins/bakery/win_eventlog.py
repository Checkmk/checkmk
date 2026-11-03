#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator

_Log = tuple[Literal["all"], None] | tuple[Literal["named"], str]


class _EventLog(BaseModel):
    log: _Log
    severity: Literal["warn", "crit", "all", "off"]
    context: bool


class _Filter(BaseModel):
    log: _Log
    include: Sequence[str]
    exclude: Sequence[str]


class _TextPattern(BaseModel):
    log: _Log
    pattern: str


class _Cluster(BaseModel):
    name: str
    ips: Sequence[str]


class _Config(BaseModel):
    event_logs: Sequence[_EventLog] | None = None
    filter_ids: Sequence[_Filter] = ()
    filter_sources: Sequence[_Filter] = ()
    filter_users: Sequence[_Filter] = ()
    text_pattern: Sequence[_TextPattern] = ()
    sendall: bool = False
    skip_duplicated: bool | None = None
    cluster_mapping: Sequence[_Cluster] = ()
    vista_api: bool | None = None


def get_win_eventlog_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield from _get_win_eventlog_config(config)
    yield from _get_win_eventlog_filters(config)
    if config.cluster_mapping:
        clusters = {}
        for cluster_config in config.cluster_mapping:
            cluster_name = cluster_config.name
            cluster_ips = list(cluster_config.ips)
            clusters[cluster_name] = cluster_ips

        yield WindowsConfigEntry(path=["logwatch", "clusters"], content=clusters)
    if config.text_pattern:
        entries = []
        for pattern in config.text_pattern:
            key = _log_key(pattern.log)
            entries.append(f"{key}:{pattern.pattern}")

        yield WindowsConfigEntry(path=["logwatch", "text_pattern"], content=entries)


def _log_key(log: _Log) -> str:
    return "*" if log[1] is None else log[1].lower()


def _get_win_eventlog_config(config: _Config) -> WindowsConfigGenerator:
    yield WindowsConfigEntry(path=["logwatch", "sendall"], content=config.sendall)

    if config.vista_api is not None:
        yield WindowsConfigEntry(path=["logwatch", "vista_api"], content=config.vista_api)

    if config.skip_duplicated is not None:
        yield WindowsConfigEntry(
            path=["logwatch", "skip_duplicated"], content=config.skip_duplicated
        )

    # An empty list is meaningful here: it replaces the default event logs of the agent.
    if config.event_logs is not None:
        entries = []
        for event_log in config.event_logs:
            key = _log_key(event_log.log)
            value = "{} {}".format(
                event_log.severity, "context" if event_log.context else "nocontext"
            )

            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "logfile"], content=entries)


def _get_win_eventlog_filters(config: _Config) -> WindowsConfigGenerator:
    if config.filter_ids:
        entries = []
        for filter_ in config.filter_ids:
            key = _log_key(filter_.log)
            value = f"{';'.join(filter_.include)};;{';'.join(filter_.exclude)}"
            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "filter_ids"], content=entries)

    if config.filter_sources:
        entries = []
        for filter_ in config.filter_sources:
            key = _log_key(filter_.log)
            value = f"{';'.join(filter_.include)};;{';'.join(filter_.exclude)}"
            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "filter_sources"], content=entries)

    if config.filter_users:
        entries = []
        for filter_ in config.filter_users:
            key = _log_key(filter_.log)
            value = f"{';'.join(filter_.include)};;{';'.join(filter_.exclude)}"
            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "filter_users"], content=entries)


register.bakery_plugin(
    name="win_eventlog",
    windows_config_function=get_win_eventlog_windows_config,
)
