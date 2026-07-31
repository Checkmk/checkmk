#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

HOST_AVAILABILITY_FAMILY = EndpointFamily(
    name="Host Availability",
    description=(
        """
Host availability data provides information about the uptime and state history of hosts
over a configurable time range. Each entry reports the total and considered duration alongside
a breakdown of seconds spent in each monitoring state (up, down, unreach, etc.).
"""
    ),
    doc_group="Monitoring",
)

SERVICE_AVAILABILITY_FAMILY = EndpointFamily(
    name="Service Availability",
    description=(
        """
Service availability data provides information about the uptime and state history of services
over a configurable time range. Each entry reports the total and considered duration alongside
a breakdown of seconds spent in each monitoring state (ok, warn, crit, unknown, etc.).
"""
    ),
    doc_group="Monitoring",
)
