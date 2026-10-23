#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

MAPS_INTERNAL_FAMILY = EndpointFamily(
    name="Maps (internal)",
    description=(
        """
Read-only lookups the Maps SPA needs from the Checkmk GUI process: object
pickers, per-object detail reads, BI aggregations, metric display semantics and
the image library. They exist because the Maps daemon owns only the live-state
plane — it has no BI, graphing or Setup knowledge and no GUI session — so these
reads are answered here, auth-scoped to the logged-in user.

Not part of the public API: the shapes track what the SPA renders and change
with it.
"""
    ),
    doc_group="Checkmk Internal",
)
