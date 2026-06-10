#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

COMMENT_FAMILY = EndpointFamily(
    name="Comments",
    description=(
        "In Checkmk you can add comments to hosts and services to store textual information"
        " related to the object. The comments can later be viewed through the user interface or"
        " read via API. You could e.g. add maintenance information about the related host or"
        " service to help your colleagues in case problems occur.\n\n"
        "The comment endpoints allow for:\n"
        "* POST creating comments for both hosts and services.\n"
        "* LIST for getting all host & service comments.\n"
        "* GET for getting a comment using its ID.\n"
        "* DELETE for deleting a comment or comments.\n\n"
        "Each host or service can have multiple comments.\n\n"
        "Related documentation\n"
        "    https://docs.checkmk.com/latest/en/commands.html#commands"
    ),
    doc_group="Monitoring",
)
