#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Hand the plugin modules of this package to pytest.

A conftest picks the plugins its suite needs by registering them in its
`pytest_addoption`, which is early enough for the plugins' own options to be
parsed:

    def pytest_addoption(parser: pytest.Parser, pluginmanager: pytest.PytestPluginManager) -> None:
        register(pluginmanager, timeouts, faked_artifacts)

"""

from types import ModuleType

import pytest


def register_pytest_plugins(
    pluginmanager: pytest.PytestPluginManager, *plugins: ModuleType
) -> None:
    """Register modules as pytest plugins, once per session.

    Several conftests of one run may ask for the same plugin, so this is idempotent.
    """
    for plugin in plugins:
        if not pluginmanager.is_registered(plugin):
            pluginmanager.register(plugin, name=plugin.__name__)
