#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Effective Maps *runtime* settings.

The daemon's runtime knobs (``SystemSettings`` — log level, SSE cadence) are
native Checkmk global settings: WATO owns them and the daemon reads the effective
values read-only from its config dir
(:mod:`cmk.maps.backend.integrations.checkmk_globals`). A value present in the
WATO globals wins; otherwise the env-seeded defaults apply. Map/object
authoring defaults are NOT here — they are GUI-owned (``cmk.maps.gui._settings``).
"""

from __future__ import annotations

import logging

from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk_globals
from cmk.maps.backend.schemas.settings import DaemonRuntime, LogLevel, SystemSettings

logger = logging.getLogger(__name__)


def get_system_settings() -> SystemSettings:
    """Return the effective ``SystemSettings`` — ``None`` for a field means *unset*.

    The two runtime knobs are individual scalar global settings, so they need no
    form-shape conversion. ``None`` (not set in WATO) is handled by the
    ``get_effective_*`` helpers, which fall back to the env-seeded defaults.
    """
    g = checkmk_globals.load_maps_globals()
    try:
        # The .mk namespace is untyped, so let pydantic do the narrowing; a bad
        # value lands in the except branch below like any other invalid global.
        return SystemSettings.model_validate(
            {
                "log_level": g[checkmk_globals.VAR_LOG_LEVEL],
                "state_refresh_interval": g[checkmk_globals.VAR_STATE_REFRESH_INTERVAL],
            }
        )
    except Exception as exc:
        logger.warning("maps system globals invalid, using defaults: %(error)s", {"error": exc})
        return SystemSettings()


def get_effective_state_refresh_interval() -> int:
    data = get_system_settings()
    # Floor at 1s: a 0 (env fat-finger or a bad WATO global) would turn the
    # broadcast loop's ``asyncio.sleep`` into a tight CPU-pinning loop that
    # hammers Livestatus every tick.
    return max(1, data.state_refresh_interval or settings.state_refresh_interval)


def apply_log_level(level: str | None) -> None:
    """Apply *level* to the root logger. Falls back to env-derived default when None."""
    effective = level or settings.log_level
    numeric = getattr(logging, effective, logging.INFO)
    logging.getLogger().setLevel(numeric)
    logger.info("Log level set to %(level)s", {"level": effective})


def get_effective_log_level() -> LogLevel:
    return get_system_settings().log_level or settings.log_level


def get_daemon_runtime() -> DaemonRuntime:
    """The resolved runtime knobs, as shipped to the client with every states payload."""
    return DaemonRuntime(
        state_refresh_interval=get_effective_state_refresh_interval(),
        log_level=get_effective_log_level(),
    )
