#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.plugin_loader import import_plugins

from cmk.gui.watolib.host_attributes import host_attribute_registry


def register() -> None:
    # This is a hack to make all host attributes available before loading the openapi plugins. The
    # modules would be loaded later on by cmk.gui.cee.agent_bakery.registration.register(), but the
    # openapi code imported here requires all host_attributes to be present before loading it.
    # This can be cleaned up once we have refactored the registration here.
    try:
        from cmk.gui.cee.agent_bakery._host_attribute import (
            HostAttributeBakeAgentPackage,  # pylint: disable=no-name-in-module
        )

        host_attribute_registry.register(HostAttributeBakeAgentPackage)
    except ImportError:
        pass

    # Will be refactored to proper registration later. For now the imports implicitly perform the
    # registration as before
    import_plugins(__file__, "cmk.gui.openapi.endpoints")
