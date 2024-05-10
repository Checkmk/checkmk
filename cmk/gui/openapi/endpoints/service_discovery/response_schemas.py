#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.response_schemas import BackgroundJobStatus, DomainObject

from cmk import fields


class DiscoveryBackgroundJobStatusObject(DomainObject):
    domainType = fields.Constant(
        "discovery_run",
        description="The domain type of the object",
    )
    extensions = fields.Nested(
        BackgroundJobStatus, description="The attributes of the background job"
    )
