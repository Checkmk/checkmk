#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helpers to test that the service names emitted by check plugins stay frozen."""

from collections.abc import Mapping, Sequence
from typing import Final

from cmk.agent_based.v2 import CheckPlugin, entry_point_prefixes
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from tests.unit.editions.lib.frozen_service_names import FROZEN_SERVICE_NAMES

RATIONALE: Final = """A service's name identifies the RRD files storing its metric history.
If the service name changes, the new name no longer matches the existing RRD files: users lose the
recorded metric history of every affected service, and there is NO migration or translation
mechanism that could restore it.  Changing a service name is therefore an incompatible
change that must not be made lightly.

How to resolve this failure:

* You added or renamed a new check plugin: freeze its service name by adding it to
  FROZEN_SERVICE_NAMES. Choose the name carefully, changing it later will have consequences.

* You changed the service name of an existing check plugin: reconsider. This
  irrevocably disconnects all users of the plugin from their recorded metric history
  and requires an incompatible werk. If the change really is justified, update the entry in
  FROZEN_SERVICE_NAMES. Consider giving the user to option to keep the old service via the via the
  "Use new service names" global setting."""


def extract_check_plugin_service_names() -> Mapping[str, str]:
    """Extract the service name template of every check plugin shipped in this edition.

    Only plugins written against the current plugin API are considered; FROZEN_SERVICE_NAMES
    also contains the legacy plugins, so coverage grows automatically as they are migrated.
    """
    discovered: DiscoveredPlugins[CheckPlugin] = discover_all_plugins(
        PluginGroup.AGENT_BASED,
        {CheckPlugin: entry_point_prefixes()[CheckPlugin]},
        skip_wrong_types=False,
        raise_errors=True,
    )
    return {plugin.name: plugin.service_name for plugin in discovered.plugins.values()}


def service_name_freeze_violations(discovered: Mapping[str, str]) -> Sequence[str]:
    return [
        (
            f"Check plugin {name!r}: service name changed from"
            f" {FROZEN_SERVICE_NAMES[name]!r} to {service_name!r}."
            if name in FROZEN_SERVICE_NAMES
            else f"New check plugin {name!r}: service name {service_name!r} is not frozen yet."
        )
        for name, service_name in sorted(discovered.items())
        if FROZEN_SERVICE_NAMES.get(name) != service_name
    ]
