#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pytest setup shared by all system test suites.

System tests run against a Checkmk site (or container) under test. Everything
here is about that: which package is tested, how long a run may take, what to
report when it fails. Suite specific setup lives in the suites' own conftests.
"""

import pytest

from tests.testlib.pytest_helpers import faked_artifacts, registration, timeouts
from tests.testlib.system.pytest_helpers import selection, sharding


def pytest_addoption(pluginmanager: pytest.PytestPluginManager) -> None:
    registration.register_pytest_plugins(
        pluginmanager, faked_artifacts, selection, sharding, timeouts
    )
