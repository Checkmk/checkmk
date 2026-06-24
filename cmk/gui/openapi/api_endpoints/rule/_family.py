#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

RULE_FAMILY = EndpointFamily(
    name="Rules",
    description=(
        "A rule is a configuration object that assigns values or conditions to hosts "
        "and services within a ruleset. Use these endpoints to create, show, list, "
        "modify, move and delete rules."
    ),
    doc_group="Setup",
)
