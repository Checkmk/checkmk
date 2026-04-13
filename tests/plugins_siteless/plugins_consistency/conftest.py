#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator

import pytest

from cmk.checkengine.plugins import AgentBasedPlugins


@pytest.fixture(scope="session")
def agent_based_plugins(tmp_path_factory: pytest.TempPathFactory) -> Generator[AgentBasedPlugins]:
    # Local import to have faster pytest initialization
    from cmk.base import config

    plugins = config.load_all_pluginX()
    assert not plugins.errors
    yield plugins
