#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
WARNING
-------

**This version of the bakery API is work in progress and not yet stable.
It might not even work at all.
It is not recommended to use this version in production systems.**



New in this version
-------------------

This section lists the most important changes you have to be
aware of when migrating your plug-in to this API version.

Note that changes are expressed in relation to the API version 1.

Registration is replaced by a discovery approach
************************************************

This is the main reason for the introduction of this new API version.
Plugins are no longer registered during import, but only created and
picked up later by the backend.
To realize this, we introduced a new class:

:class:`BakeryPlugin` replacing :func:`register.bakery_plugin`

The arguments of these have barely changed (see next paragraph), resulting
in easy to automate changes.

To be picked up by the backend, plugins need to be put in the right folder.
This is described in the section :ref:`plugin-location-and-loading`.

Example:
########

We register the bakery plugin for our ceph integration from the file
``~/lib/python3/cmk/plugins/ceph/bakery/ceph.py``::

    #!/usr/bin/env/python3
    ...
    bakery_plugin_ceph = BakeryPlugin(
        name="ceph",
        parameter_parser=CephConfig.model_validate,
        files_function=get_ceph_files,
    )



Changed arguments and validation for bakery plug-ins
****************************************************

We slightly adopted the arguments to the above-mentioned `BakeryPlugin` class
compared to the former registry function.
We now favor type annotations over runtime validation.
To get slightly easier type annotations, we introduced the `parameter_parser` argument.
It is strongly recommended to use this argument -- but if you insist to not use it (maybe
for easier migration), you can use the :func:`no_op_parser` function.)


Removed `password_store`
************************

We no longer expose the password_store and its (currently not stable) API to the bakery plug-ins.
Instead, consumers of a `Password` form spec element will be passed an instance of a dedicated
API class: :class:`Secret`.
Using this, plug-ins can access the secret directly.

"""

from cmk.bakery.v1 import DebStep as DebStep
from cmk.bakery.v1 import FileGenerator as FileGenerator
from cmk.bakery.v1 import OS as OS
from cmk.bakery.v1 import PkgStep as PkgStep
from cmk.bakery.v1 import Plugin as Plugin
from cmk.bakery.v1 import PluginConfig as PluginConfig
from cmk.bakery.v1 import RpmStep as RpmStep
from cmk.bakery.v1 import Scriptlet as Scriptlet
from cmk.bakery.v1 import ScriptletGenerator as ScriptletGenerator
from cmk.bakery.v1 import SolStep as SolStep
from cmk.bakery.v1 import SystemBinary as SystemBinary
from cmk.bakery.v1 import SystemConfig as SystemConfig
from cmk.bakery.v1 import WindowsConfigContent as WindowsConfigContent
from cmk.bakery.v1 import WindowsConfigEntry as WindowsConfigEntry
from cmk.bakery.v1 import WindowsConfigGenerator as WindowsConfigGenerator
from cmk.bakery.v1 import WindowsConfigItems as WindowsConfigItems
from cmk.bakery.v1 import WindowsGlobalConfigEntry as WindowsGlobalConfigEntry
from cmk.bakery.v1 import WindowsSystemConfigEntry as WindowsSystemConfigEntry

from ._config import Secret as Secret
from ._plugins import BakeryPlugin as BakeryPlugin
from ._plugins import entry_point_prefixes as entry_point_prefixes
from ._plugins import no_op_parser as no_op_parser

# We need this for the sphinx doc :-/
__all__ = [
    # New in v2
    "BakeryPlugin",
    "Secret",
    "no_op_parser",
    # Re-exported from v1
    "DebStep",
    "FileGenerator",
    "OS",
    "PkgStep",
    "Plugin",
    "PluginConfig",
    "RpmStep",
    "Scriptlet",
    "ScriptletGenerator",
    "SolStep",
    "SystemBinary",
    "SystemConfig",
    "WindowsConfigContent",
    "WindowsConfigEntry",
    "WindowsConfigGenerator",
    "WindowsConfigItems",
    "WindowsGlobalConfigEntry",
    "WindowsSystemConfigEntry",
    # Entry point prefixes
    "entry_point_prefixes",
]
