#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from omdlib.ai_agent_engine import AI_AGENT_ENGINE
from omdlib.config_hooks import get_hook

from cmk.ccc.version import Edition


@pytest.mark.parametrize("edition", list(Edition), ids=lambda e: e.name.lower())
def test_ai_agent_engine_ships_disabled(edition: Edition) -> None:
    assert AI_AGENT_ENGINE.default(edition) == "off"


def test_ai_agent_engine_hook_is_registered() -> None:
    assert get_hook(AI_AGENT_ENGINE.name) is AI_AGENT_ENGINE
