#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

CRASH_REPORT_FAMILY = EndpointFamily(
    name="Crash reports (internal)",
    description=(
        "A crash report collects the context of an unhandled error so that it can be\n"
        "reviewed later and reported to the Checkmk team. Errors that happen in the\n"
        "browser are invisible to the Checkmk server, so the frontend reports them\n"
        "through this family."
    ),
    doc_group="Checkmk Internal",
)
