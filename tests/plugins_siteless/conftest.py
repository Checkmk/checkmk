#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.pytest_helpers import registration, timeouts


def pytest_addoption(parser: pytest.Parser, pluginmanager: pytest.PytestPluginManager) -> None:
    registration.register_pytest_plugins(pluginmanager, timeouts)
    parser.addoption(
        "--store",
        action="store_true",
        default=False,
        help="Store the services' states in the test data directory.",
    )
