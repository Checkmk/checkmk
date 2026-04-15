#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

PAGETYPE_TOPIC_FAMILY = EndpointFamily(
    name="Pagetype Topics",
    description="""Pagetype topics are the different topics that Dashboards, Views etc. can be grouped into.""",
    doc_group="Checkmk Internal",
)
