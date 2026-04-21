#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

BACKGROUND_JOB_FAMILY = EndpointFamily(
    name="Background Jobs",
    description=(
        """A background job allows certain tasks to be run as background processes. It should be
kept in mind that some jobs lock certain areas in the Setup to prevent further configurations as
long as the background process is running."""
    ),
    doc_group="Checkmk Internal",
)
