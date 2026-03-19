#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.http import request
from cmk.gui.quick_setup._modes import ModeConfigurationBundle
from cmk.gui.watolib.configuration_bundle_store import ConfigBundleStore


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason=(
        "Crash report e112cabe-c3c7-11f0-b7a7-020bc683718f: ModeConfigurationBundle.action()"
        " crashes with AttributeError when the bundle no longer exists at save time"
        " (self._bundle is never set when self._existing_bundle is False)"
    ),
)
def test_mode_configuration_bundle_action_crashes_when_bundle_missing(
    request_context: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Reproduces the crash: if the bundle disappears between GET (form render) and
    # POST (save), _from_vars() sets self._existing_bundle=False and returns early
    # without setting self._bundle. action() then crashes accessing self._bundle.
    request.set_var("bundle_id", "azure_config_2")
    monkeypatch.setattr(ConfigBundleStore, "load_for_reading", lambda self: {})

    # __init__ calls _from_vars(), which finds the bundle missing and returns early
    # without setting self._bundle — exactly mirroring the crash scenario.
    mode = ModeConfigurationBundle()

    # This is the crashing line in action() when _save is submitted:
    mode._bundle.update({"title": "test", "comment": ""})  # AttributeError!
