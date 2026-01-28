#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

CURRENT_EVENTS_FAMILY = EndpointFamily(
    name="Event Console",
    description=(
        """With the Event Console (EC), Checkmk provides a fully integrated system for monitoring
events from sources including syslog, SNMP traps, Windows Event Logs, log files, and custom
applications.

These endpoints let you query current Event Console events, inspect individual events, update
their phase, change their state, and archive matching events."""
    ),
    doc_group="Monitoring",
)
