#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.checkengine.plugins import AgentBasedPlugins
from tests.testlib.common.repo import repo_path


@pytest.fixture(scope="session")
def agent_based_plugins() -> AgentBasedPlugins:
    # Local import to have faster pytest initialization
    from cmk.base import config

    plugins = config.load_all_pluginX(repo_path() / "cmk/base/legacy_checks")
    assert not plugins.errors
    return plugins
