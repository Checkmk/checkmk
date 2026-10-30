#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The gate deciding whether the service slide-in offers an AI explanation.

Tests build their own instance rather than touching the module-level singleton, so an
edition registering itself elsewhere in the session cannot decide the outcome here.
"""

from cmk.gui.monitor.services._ai_explain import AiExplain


def test_the_gate_is_consulted_on_every_render_rather_than_at_registration() -> None:
    """A user losing the permission, or the setting being turned off, takes effect at once."""
    enabled = True
    rendered = []
    ai_explain = AiExplain()
    ai_explain.register(is_enabled=lambda: enabled, render_listener=lambda: rendered.append("yes"))

    ai_explain.render_listener()
    enabled = False
    ai_explain.render_listener()

    assert rendered == ["yes"]
