#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.discover_plugins import discover_plugins, DiscoveredPlugins
from cmk.rulesets.v1 import RuleSpec


def load_api_v1_rulespecs(raise_errors: bool) -> tuple[Sequence[str], Mapping[str, RuleSpec]]:
    discovered_plugins: DiscoveredPlugins[RuleSpec] = discover_plugins(
        "rulesets",
        "rulespec_",
        RuleSpec,
        raise_errors=raise_errors,
    )
    errors = [str(e) for e in discovered_plugins.errors]
    loaded = {plugin.name: plugin for plugin in discovered_plugins.plugins.values()}

    # TODO:
    #  * see if we really need to return the errors. Maybe we can just either ignore or raise them.
    #  * deal with duplicate names.
    return errors, loaded
