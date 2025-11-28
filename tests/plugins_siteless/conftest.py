#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--store",
        action="store_true",
        default=False,
        help="Store the services' states in the test data directory.",
    )
