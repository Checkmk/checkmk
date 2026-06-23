#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

AUTOCOMPLETE_FAMILY = EndpointFamily(
    name="Autocomplete (internal)",
    description=(
        "This provides access to autocomplete functionality. This currently is mostly used\n"
        "internally by the Grafana's data source plug-in and relies on data sent by it that\n"
        "is not fully documented and specified yet."
    ),
    doc_group="Checkmk Internal",
)
