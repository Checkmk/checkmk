#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from typing import Any

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


def get_win_eventlog_windows_config(conf: dict[str, Any]) -> WindowsConfigGenerator:
    yield from _get_win_eventlog_config(conf)
    yield from _get_win_eventlog_filters(conf)
    if "cluster_mapping" in conf:
        clusters = {}
        for cluster_config in conf["cluster_mapping"]:
            cluster_name = cluster_config["name"]
            cluster_ips = cluster_config["ips"]
            clusters[cluster_name] = cluster_ips

        yield WindowsConfigEntry(path=["logwatch", "clusters"], content=clusters)
    if "text_pattern" in conf:
        entries = []
        for name, value in conf["text_pattern"]:
            key = name.lower()
            entries.append(f"{key}:{value}")

        yield WindowsConfigEntry(path=["logwatch", "text_pattern"], content=entries)


def _get_win_eventlog_config(conf: dict[str, Any]) -> WindowsConfigGenerator:
    yield WindowsConfigEntry(path=["logwatch", "sendall"], content=conf.get("sendall", False))

    if "vista_api" in conf:
        yield WindowsConfigEntry(
            path=["logwatch", "vista_api"], content=conf.get("vista_api", False)
        )

    if "skip_duplicated" in conf:
        yield WindowsConfigEntry(
            path=["logwatch", "skip_duplicated"], content=conf.get("skip_duplicated", False)
        )

    if "logfiles" in conf:
        entries = []
        for name, severity, context in conf["logfiles"]:
            key = name.lower()
            value = "{} {}".format(severity, "context" if context else "nocontext")

            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "logfile"], content=entries)


def _get_win_eventlog_filters(conf: dict[str, Any]) -> WindowsConfigGenerator:
    if "filter_ids" in conf:
        entries = []
        for name, includes, excludes in conf["filter_ids"]:
            key = name.lower()
            value = f"{';'.join(includes)};;{';'.join(excludes)}"
            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "filter_ids"], content=entries)

    if "filter_sources" in conf:
        entries = []
        for name, includes, excludes in conf["filter_sources"]:
            key = name.lower()
            value = f"{';'.join(includes)};;{';'.join(excludes)}"
            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "filter_sources"], content=entries)

    if "filter_users" in conf:
        entries = []
        for name, includes, excludes in conf["filter_users"]:
            key = name.lower()
            value = f"{';'.join(includes)};;{';'.join(excludes)}"
            entries.append({key: value})

        yield WindowsConfigEntry(path=["logwatch", "filter_users"], content=entries)


register.bakery_plugin(
    name="win_eventlog",
    windows_config_function=get_win_eventlog_windows_config,
)
