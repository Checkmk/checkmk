#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.plugin_classes import LegacyPluginLocation

from cmk.discover_plugins import PluginLocation

_PLUGINS_FILE_NAME = "inventory_plugins_index.json"


@dataclass(frozen=True)
class PluginIndex:
    legacy: Sequence[str]
    locations: Sequence[PluginLocation]


def make_index_file(config_path: Path) -> Path:
    return Path(config_path, _PLUGINS_FILE_NAME)


def load_plugin_index(config_path: Path) -> PluginIndex:
    raw = json.loads(make_index_file(config_path).read_text())
    return PluginIndex(
        legacy=[str(f) for f in raw["legacy"]],
        locations=[PluginLocation.from_str(loc) for loc in raw["locations"]],
    )


def create_plugin_index(plugins: agent_based_register.AgentBasedPlugins) -> str:
    sections = agent_based_register.filter_relevant_raw_sections(
        consumers=plugins.inventory_plugins.values(),
        sections=[*plugins.agent_sections.values(), *plugins.snmp_sections.values()],
    )
    raw = {
        "locations": [
            *(str(p.location) for p in sections.values() if isinstance(p.location, PluginLocation)),
            *(str(p.location) for p in plugins.inventory_plugins.values()),
        ],
        "legacy": [
            p.location.file_name
            for p in sections.values()
            if isinstance(p.location, LegacyPluginLocation)
        ],
    }
    return json.dumps(raw)
