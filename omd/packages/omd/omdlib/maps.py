#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from omdlib.config_api import Hook, null_action

# The daemon binds a Unix socket under tmp/run (no TCP port to template into the
# Apache reverse proxy), so only the on/off switch is needed. Maps ships in every
# edition, so the hook defaults to "on" everywhere the hook file is present.
MAPS = Hook(
    name="MAPS",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "on",
    activation=null_action,
)
