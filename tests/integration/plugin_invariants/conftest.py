#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator

import pytest

from cmk.checkengine.plugin_backend import load_all_plugins
from cmk.checkengine.plugins import AgentBasedPlugins


@pytest.fixture(scope="session")
def agent_based_plugins() -> Generator[AgentBasedPlugins]:
    yield load_all_plugins(raise_errors=True)
