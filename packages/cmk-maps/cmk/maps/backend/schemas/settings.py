#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Daemon runtime settings schema.

``SystemSettings`` — the daemon's runtime knobs (log level, SSE cadence), native
Checkmk global settings the daemon reads. Map/object authoring *defaults* are
GUI-owned (``cmk.maps.gui._settings``) and no longer modelled here.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class SystemSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Backend log verbosity and SSE poll cadence. Each is an individual Checkmk
    # global setting (Customize → Maps → "Maps settings"); the daemon reads
    # the effective value. ``None`` means "not set in WATO" → the daemon uses its
    # env-seeded default (``core/config.py`` ``Settings``).
    log_level: LogLevel | None = None
    state_refresh_interval: Annotated[int, Field(ge=1, le=300)] | None = None


class DaemonRuntime(BaseModel):
    """``SystemSettings`` resolved to the values the daemon is actually running on.

    Where ``SystemSettings`` models what WATO stored (``None`` = unset), this is
    what came out of it after the env-seeded fallbacks were applied — so every
    field is a concrete value. It rides along with the states the daemon
    produces, which is how the client learns the broadcast cadence: it needs
    that for its polling fallback, i.e. exactly when the SSE stream is down and
    no in-band stream message could reach it.
    """

    model_config = ConfigDict(extra="ignore")

    state_refresh_interval: int
    log_level: LogLevel
