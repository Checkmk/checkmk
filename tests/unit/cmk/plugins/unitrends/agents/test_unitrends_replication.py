#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Smoke test for the unitrends_replication agent plug-in.

Keep this module compatible with the oldest Python we support for agent
plug-ins: no f-strings, no variable annotations, no typing imports.
"""

from cmk.plugins.unitrends.agents import unitrends_replication


def test_plugin_is_importable():
    # type: () -> None
    """Guards against syntax and imports that are too new for old agents."""
    assert unitrends_replication.__version__
