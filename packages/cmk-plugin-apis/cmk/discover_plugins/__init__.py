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

from ._libexec import (
    discover_executable as discover_executable,
)
from ._libexec import (
    family_libexec_dir as family_libexec_dir,
)
from ._python_plugins import (
    addons_plugins_local_path as addons_plugins_local_path,
)
from ._python_plugins import (
    Collector as Collector,
)
from ._python_plugins import (
    discover_all_plugins as discover_all_plugins,
)
from ._python_plugins import (
    discover_families as discover_families,
)
from ._python_plugins import (
    discover_modules as discover_modules,
)
from ._python_plugins import (
    discover_plugins_from_modules as discover_plugins_from_modules,
)
from ._python_plugins import (
    discover_submodules as discover_submodules,
)
from ._python_plugins import (
    DiscoveredPlugins as DiscoveredPlugins,
)
from ._python_plugins import (
    PluginLocation as PluginLocation,
)
from ._python_plugins import (
    plugins_local_path as plugins_local_path,
)
from ._wellknown import (
    AGENT_PLUGINS_FOLDER as AGENT_PLUGINS_FOLDER,
)
from ._wellknown import (
    CMK_ADDONS_PLUGINS as CMK_ADDONS_PLUGINS,
)
from ._wellknown import (
    CMK_PLUGINS as CMK_PLUGINS,
)
from ._wellknown import (
    PluginGroup as PluginGroup,
)
