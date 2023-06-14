#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.fields.utils import BaseSchema
from cmk.gui.plugins.openapi.restful_objects.response_schemas import DomainObject

from cmk import fields


class JobLogs(BaseSchema):
    result = fields.List(
        fields.String(),
        description="The list of result related logs",
    )
    progress = fields.List(
        fields.String(),
        description="The list of progress related logs",
    )


class BackgroundJobStatus(BaseSchema):
    active = fields.Boolean(
        required=True,
        description="This field indicates if the background job is active or not.",
        example=True,
    )
    state = fields.String(
        required=True,
        description="This field indicates the current state of the background job.",
        enum=["initialized", "running", "finished", "stopped", "exception"],
        example="initialized",
    )
    logs = fields.Nested(
        JobLogs,
        required=True,
        description="Logs related to the background job.",
        example={"result": ["result1"], "progress": ["progress1"]},
    )


class DiscoveryBackgroundJobStatusObject(DomainObject):
    domainType = fields.Constant(
        "discovery_run",
        description="The domain type of the object",
    )
    extensions = fields.Nested(
        BackgroundJobStatus, description="The attributes of the background job"
    )
