#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from omdlib.config_api import Hook, null_action, PortHook

OPENTELEMETRY_COLLECTOR = Hook(
    name="OPENTELEMETRY_COLLECTOR",
    default=lambda _edition: "off",
    activation=null_action,
    choices=[("on", "enable"), ("off", "disable")],
)

OPENTELEMETRY_COLLECTOR_SELF_MONITORING_PORT = PortHook(
    name="OPENTELEMETRY_COLLECTOR_SELF_MONITORING_PORT",
    display_name="Otel Collector self-monitoring port",
    default_port=14317,
    activation=null_action,
    choices=re.compile(r"[0-9]{1,5}$"),
)
