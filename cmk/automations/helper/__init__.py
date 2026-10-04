#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The automation helper: a server that keeps the automation engine loaded.

It serves the automations over a unix socket, and reloads the configuration
whenever the watcher reports a change. What runs it, and how the engine gets
its configuration, is up to the caller.
"""

from ._app import make_application
from ._cache import Cache
from ._config import config_from_disk_or_default_config
from ._server import run as run_server
from ._tracer import configure_tracer
from ._watcher import run as run_watcher

__all__ = [
    "Cache",
    "config_from_disk_or_default_config",
    "configure_tracer",
    "make_application",
    "run_server",
    "run_watcher",
]
