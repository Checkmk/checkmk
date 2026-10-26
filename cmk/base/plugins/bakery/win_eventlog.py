#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator

# The rule set stores an empty string for "include all" or "exclude none".
_Names = Sequence[str] | Literal[""]


class _Cluster(BaseModel):
    name: str
    ips: Sequence[str]


class _Config(BaseModel):
    logfiles: Sequence[tuple[str, str, bool]] | None = None
    filter_ids: Sequence[tuple[str, _Names, _Names]] | None = None
    filter_sources: Sequence[tuple[str, _Names, _Names]] | None = None
    filter_users: Sequence[tuple[str, _Names, _Names]] | None = None
    text_pattern: Sequence[tuple[str, str]] | None = None
    sendall: bool = False
    skip_duplicated: bool | None = None
    cluster_mapping: Sequence[_Cluster] | None = None
    vista_api: bool | None = None


def get_win_eventlog_windows_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield from _get_win_eventlog_config(config)
    yield from _get_win_eventlog_filters(config)
    if config.cluster_mapping is not None:
        clusters = {}
        for cluster_config in config.cluster_mapping:
            cluster_name = cluster_config.name
            cluster_ips = list(cluster_config.ips)
            clusters[cluster_name] = cluster_ips

        yield WindowsConfigEntry(path=["logwatch", "clusters"], content=clusters)
    if config.text_pattern is not None:
        entries = []
        for name, value in config.text_pattern:
            key = name.lower()
            entries.append(f"{key}:{value}")

        yield WindowsConfigEntry(path=["logwatch", "text_pattern"], content=entries)


def _get_win_eventlog_config(config: _Config) -> WindowsConfigGenerator:
    yield WindowsConfigEntry(path=["logwatch", "sendall"], content=config.sendall)

    if config.vista_api is not None:
        yield WindowsConfigEntry(path=["logwatch", "vista_api"], content=config.vista_api)

    if config.skip_duplicated is not None:
        yield WindowsConfigEntry(
            path=["logwatch", "skip_duplicated"], content=config.skip_duplicated
        )

    if config.logfiles is not None:
        entries = []
        for name, severity, context in config.logfiles:
            key = name.lower()
            value = "{} {}".format(severity, "context" if context else "nocontext")

            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "logfile"], content=entries)


def _get_win_eventlog_filters(config: _Config) -> WindowsConfigGenerator:
    if config.filter_ids is not None:
        entries = []
        for name, includes, excludes in config.filter_ids:
            key = name.lower()
            value = f"{';'.join(includes)};;{';'.join(excludes)}"
            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "filter_ids"], content=entries)

    if config.filter_sources is not None:
        entries = []
        for name, includes, excludes in config.filter_sources:
            key = name.lower()
            value = f"{';'.join(includes)};;{';'.join(excludes)}"
            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "filter_sources"], content=entries)

    if config.filter_users is not None:
        entries = []
        for name, includes, excludes in config.filter_users:
            key = name.lower()
            value = f"{';'.join(includes)};;{';'.join(excludes)}"
            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "filter_users"], content=entries)


register.bakery_plugin(
    name="win_eventlog",
    windows_config_function=get_win_eventlog_windows_config,
)
