#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

QUICK_SETUP_FAMILY = EndpointFamily(
    name="Quick setup",
    description=(
        "* GET quick setup guided stages or overview stages\n"
        "* GET a quick setup stage structure\n"
        "* POST validate stage\n"
        "* POST complete the quick setup and save"
    ),
    doc_group="Checkmk Internal",
)
