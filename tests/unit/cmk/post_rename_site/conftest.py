#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from tests.testlib.gui.common_fixtures import perform_load_plugins


@pytest.fixture(scope="session", autouse=True)
def load_plugins(test_edition: Edition) -> None:
    """The rename actions rely on the GUI plug-in registration (host attributes,
    folder validators, site management, rulespecs)"""
    perform_load_plugins(test_edition)
