#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Loading API based plugins from cmk.plugins

This implements common logic for loading API based plugins
(yes, we have others) from cmk.plugins.

We have more "plugin" loading logic else where, but there
are subtle differences with respect to the treatment of
namespace packages and error handling.

Changes in this file might result in different behaviour
of plugins developed against a versionized API.

Please keep this in mind when trying to consolidate.
"""

from ._libexec import discover_executable, family_libexec_dir
from ._python_plugins import (
    addons_plugins_local_path,
    Collector,
    discover_all_plugins,
    discover_families,
    discover_modules,
    discover_plugins_from_modules,
    DiscoveredPlugins,
    PluginLocation,
    plugins_local_path,
)
from ._wellknown import PluginGroup

__all__ = [
    "addons_plugins_local_path",
    "Collector",
    "DiscoveredPlugins",
    "discover_executable",
    "discover_families",
    "discover_modules",
    "discover_all_plugins",
    "discover_plugins_from_modules",
    "family_libexec_dir",
    "PluginGroup",
    "PluginLocation",
    "plugins_local_path",
]
