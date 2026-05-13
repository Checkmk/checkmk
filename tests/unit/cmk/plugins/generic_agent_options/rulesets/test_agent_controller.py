#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.generic_agent_options.rulesets.agent_controller import migrate


@pytest.mark.parametrize(
    "value,expected",
    [
        # Old format: (True, {}) tuple
        (
            {"agent_ctl_enabled": (True, {})},
            {"agent_ctl_enabled": ("enabled", {})},
        ),
        # Old format: (True, {"detect_proxy": True}) tuple
        (
            {"agent_ctl_enabled": (True, {"detect_proxy": True})},
            {"agent_ctl_enabled": ("enabled", {"detect_proxy": True})},
        ),
        # Old format: (False, None) tuple
        (
            {"agent_ctl_enabled": (False, None)},
            {"agent_ctl_enabled": ("disabled", None)},
        ),
        # Already migrated: enabled
        (
            {"agent_ctl_enabled": ("enabled", {})},
            {"agent_ctl_enabled": ("enabled", {})},
        ),
        # Already migrated: disabled
        (
            {"agent_ctl_enabled": ("disabled", None)},
            {"agent_ctl_enabled": ("disabled", None)},
        ),
        # No agent_ctl_enabled key: pass through
        (
            {"other_key": "value"},
            {"other_key": "value"},
        ),
    ],
)
def test_migrate(value: object, expected: object) -> None:
    assert migrate(value) == expected
