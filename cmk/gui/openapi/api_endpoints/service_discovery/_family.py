#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

SERVICE_DISCOVERY_FAMILY = EndpointFamily(
    name="Service discovery",
    description=(
        """A service discovery is the automatic and reliable detection of all services to be monitored on
a host.

You can find an introduction to services including service discovery in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_services.html)."""
    ),
    doc_group="Setup",
)
