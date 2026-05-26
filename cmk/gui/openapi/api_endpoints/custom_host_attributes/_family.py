#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

CUSTOM_HOST_ATTR_FAMILY = EndpointFamily(
    name="Custom host attributes",
    description=(
        "Custom host attributes extend the host data model with arbitrary text fields.\n"
        "They can be created, updated, and deleted via this API."
    ),
    doc_group="Setup",
)
