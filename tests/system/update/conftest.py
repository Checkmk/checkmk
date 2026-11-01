#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.system.update import pytest_plugin
from tests.testlib.pytest_helpers import registration


def pytest_addoption(pluginmanager: pytest.PytestPluginManager) -> None:
    registration.register_pytest_plugins(pluginmanager, pytest_plugin)
