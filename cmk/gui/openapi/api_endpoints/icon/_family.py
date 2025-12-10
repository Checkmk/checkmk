#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

ICON_FAMILY = EndpointFamily(
    name="Icons",
    description="""Icons used throughout the Checkmk GUI.""",
    doc_group="Checkmk Internal",
)
