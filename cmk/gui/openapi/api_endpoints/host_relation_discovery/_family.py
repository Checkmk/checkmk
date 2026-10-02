#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

HOST_RELATION_DISCOVERY_FAMILY = EndpointFamily(
    name="Host relation discovery",
    description=(
        """Find the relations the hosts in Setup already show - a management board named
after the host it sits in, or two hosts carrying the same serial number - and store the
ones that are accepted. A scan and the run storing from it are background jobs, and
what a scan found is read a page at a time. Backs the "Relation detection" page of the
Setup and is not part of the public API."""
    ),
    doc_group="Checkmk Internal",
)
