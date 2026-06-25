#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI↔daemon contract: the daemon reading its RUNTIME globals from its config dir.

The daemon owns only its runtime knobs (``maps_connections``, ``maps_log_level``,
``maps_state_refresh_interval``) in ``etc/check_mk/maps.d/wato/`` (``global.mk`` +
per-site ``sitespecific.mk``). These tests pin the read + site-specific merge.
Map/object authoring defaults are GUI-owned now (see the GUI-side
``test_settings.py``), so their flatten is no longer tested here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk_globals
from cmk.maps.backend.services import settings_service
from cmk.maps.shared.config_vars import (
    VAR_CONNECTIONS,
    VAR_LOG_LEVEL,
    VAR_STATE_REFRESH_INTERVAL,
)


def _write_maps_wato(wato_dir: Path, *, global_mk: str = "", sitespecific_mk: str = "") -> None:
    wato_dir.mkdir(parents=True, exist_ok=True)
    if global_mk:
        (wato_dir / "global.mk").write_text(global_mk)
    if sitespecific_mk:
        (wato_dir / "sitespecific.mk").write_text(sitespecific_mk)


def test_load_maps_globals_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checkmk_globals, "_maps_wato_dir", lambda: tmp_path)
    assert checkmk_globals.load_maps_globals() == {
        VAR_CONNECTIONS: None,
        VAR_LOG_LEVEL: None,
        VAR_STATE_REFRESH_INTERVAL: None,
    }


def test_sitespecific_overrides_global(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_maps_wato(
        tmp_path,
        global_mk="maps_state_refresh_interval = 5\n",
        sitespecific_mk="maps_state_refresh_interval = 30\n",
    )
    monkeypatch.setattr(checkmk_globals, "_maps_wato_dir", lambda: tmp_path)
    assert checkmk_globals.load_maps_globals()[VAR_STATE_REFRESH_INTERVAL] == 30


def test_get_system_settings_reads_scalar_globals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_maps_wato(
        tmp_path,
        global_mk="maps_log_level = 'WARNING'\nmaps_state_refresh_interval = 12\n",
    )
    monkeypatch.setattr(checkmk_globals, "_maps_wato_dir", lambda: tmp_path)
    s = settings_service.get_system_settings()
    assert s.log_level == "WARNING"
    assert s.state_refresh_interval == 12


def test_daemon_runtime_resolves_the_wato_globals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This is what travels to the client with every states payload, so it has to
    # be the value the daemon acts on, not the raw stored one.
    _write_maps_wato(
        tmp_path,
        global_mk="maps_log_level = 'WARNING'\nmaps_state_refresh_interval = 12\n",
    )
    monkeypatch.setattr(checkmk_globals, "_maps_wato_dir", lambda: tmp_path)
    runtime = settings_service.get_daemon_runtime()
    assert runtime.state_refresh_interval == 12
    assert runtime.log_level == "WARNING"


def test_daemon_runtime_falls_back_to_the_env_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Nothing configured in WATO: the client still gets concrete values rather
    # than the ``None``s ``SystemSettings`` models for "unset".
    monkeypatch.setattr(checkmk_globals, "_maps_wato_dir", lambda: tmp_path)
    runtime = settings_service.get_daemon_runtime()
    assert runtime.state_refresh_interval == settings.state_refresh_interval
    assert runtime.log_level == settings.log_level
