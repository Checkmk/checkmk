#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Container, Iterable
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path

from cmk.discover_plugins import discover_families


@dataclass(frozen=True)
class PluginFamily:
    name: str


class NotSupportedError(ValueError):
    pass


def relay_compatible_plugin_families(local_root: Path) -> Container[PluginFamily]:
    return [
        *(
            PluginFamily(ep.name)
            for ep in entry_points(group="cmk.special_agent_supported_on_relay")
        ),
        *_discover_local_plugin_families(local_root),
    ]


def _discover_local_plugin_families(local_root: Path) -> Iterable[PluginFamily]:
    return [
        PluginFamily(module.split(".")[2])
        for module, (first_path, *_) in discover_families(raise_errors=False).items()
        if first_path.startswith(str(local_root))
    ]
