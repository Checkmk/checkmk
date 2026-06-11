#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

MASTER_CONTROL_FAMILY = EndpointFamily(
    name="Master control",
    description="""\
The master control switches central monitoring functions of a site on and off. These functions
are a fixed set: notifications, service checks, host checks, flap detection, event handlers and
performance data processing.

These settings are applied to the monitoring core at runtime. They are not persisted across a
core restart.
""",
    doc_group="Monitoring",
)
