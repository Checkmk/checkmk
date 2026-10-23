#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

MAPS_FAMILY = EndpointFamily(
    name="Maps",
    description=(
        """
Checkmk Maps are visual dashboards (topology, worldmap, folder tree, presentation
slides, …) that render live monitoring state. These endpoints manage the map
configuration — creating, updating, listing and deleting maps — in the same way
the Maps editor does, so maps can be provisioned and version-controlled through
the REST-API. The live monitoring state itself is served by the Maps daemon, not
by these endpoints.
"""
    ),
    doc_group="Monitoring",
)
