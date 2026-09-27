#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

GUI_SESSION_FAMILY = EndpointFamily(
    name="GUI sessions (internal)",
    description=(
        "Lets site-internal services such as the AI control plane find the user "
        "behind a GUI session, and get an access token on that user's behalf. "
        "Only callers holding the site-internal secret may use these endpoints."
    ),
    doc_group="Checkmk Internal",
)
