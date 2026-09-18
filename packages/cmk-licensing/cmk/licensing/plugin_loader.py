#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Loading of the discoverable licensing plug-ins"""

from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.licensing.internal import entry_point_prefixes, LicenseUsageCounter


def discover_licensing_plugins(*, raise_errors: bool) -> DiscoveredPlugins[LicenseUsageCounter]:
    """Discover all licensing plug-ins

    Callers must surface the returned errors (log or raise), never drop them.
    """
    return discover_all_plugins(
        PluginGroup.LICENSING,
        entry_point_prefixes(),
        skip_wrong_types=False,
        raise_errors=raise_errors,
    )
