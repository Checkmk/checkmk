#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

AUDIT_LOG_FAMILY = EndpointFamily(
    name="Audit log",
    description="""\
The audit log records the activities taking place in Checkmk. These endpoints allow
you to read and clean these logs.
""",
    doc_group="Setup",
)
