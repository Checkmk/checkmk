#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

# Note: tests.plugins_consistency.common_tests needs to stay in the runfiles!
# There are tests living there.
from tests.plugins_consistency.common_tests.fixtures import agent_based_plugins

agent_based_plugins = pytest.fixture(scope="session")(agent_based_plugins)
