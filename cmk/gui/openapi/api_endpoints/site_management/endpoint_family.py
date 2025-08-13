#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

SITE_MANAGEMENT_FAMILY = EndpointFamily(
    name="Site management",
    description=(
        """

Site Management

The site management endpoints give you the flexibility to configure connections with
distributed sites the same way you would via the web interface.

The site management endpoints allow for:

* POST for creating new site configurations.
* PUT for updating current site configurations.
* LIST for listing all current site configurations.
* GET for getting a single site configuration.
* DELETE for deleting a single site configuration via its site id.
* LOGIN for logging into an existing site.
* LOGOUT for logging out of an existing site.

"""
    ),
    doc_group="Setup",
)
