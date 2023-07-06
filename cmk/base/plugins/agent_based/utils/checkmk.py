#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from enum import Enum
from typing import Mapping, NamedTuple, Optional, Sequence

CheckmkSection = Mapping[str, Optional[str]]


class Plugin(NamedTuple):
    name: str
    version: str
    version_int: Optional[int]
    cache_interval: Optional[int]


class PluginSection(NamedTuple):
    plugins: Sequence[Plugin]
    local_checks: Sequence[Plugin]


class ControllerSection(NamedTuple):
    # Currently this is all we need. Extend on demand...
    allow_legacy_pull: bool
    socket_ready: bool
    ip_allowlist: tuple[str, ...]


class CachedPluginType(str, Enum):
    PLUGIN = "plugins"
    LOCAL = "local"
    ORACLE = "oracle"
    MRPE = "mrpe"


class CachedPlugin(NamedTuple):
    plugin_type: CachedPluginType | None
    plugin_name: str
    timeout: int
    pid: int


class CachedPluginsSection(NamedTuple):
    timeout: list[CachedPlugin] | None
    killfailed: list[CachedPlugin] | None
