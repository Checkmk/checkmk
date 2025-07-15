#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk import fields
from cmk.gui.fields.base import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject


class StatusLogInfo(BaseSchema):
    JobProgressUpdate = fields.List(
        fields.String,
        description="The progress update logs of the background job",
        example=["Parsed configuration", "Saved configuration"],
    )
    JobResult = fields.List(
        fields.String,
        description="The result logs of the background job",
        example=["Job finished"],
    )
    JobException = fields.List(
        fields.String,
        description="The exception logs of the background job",
        example=["error_1", "error_2"],
    )


class BackgroundJobStatus(BaseSchema):
    # TODO add more fields
    state = fields.String(
        required=True,
        description="The state of the background job",
        example="finished",
    )
    log_info = fields.Nested(
        StatusLogInfo,
        description="The logs of the background job",
        example={
            "JobProgressUpdate": ["Parsed configuration", "Saved configuration"],
            "JobResult": ["Job finished"],
            "JobException": ["error_1", "error_2"],
        },
    )


class BackgroundJobSnapshot(BaseSchema):
    # TODO add more fields
    site_id = fields.String(
        required=True,
        description="The site ID where the background job is located",
        example="foobar",
    )
    status = fields.Nested(
        BackgroundJobStatus,
        description="The status of the background job",
        example={},
    )
    active = fields.Boolean(
        required=True,
        description="This field indicates if the background job is running.",
        example=True,
    )


class BackgroundJobSnapshotObject(DomainObject):
    domainType = fields.Constant(
        "background_job",
        description="The domain type of the object",
    )
    extensions = fields.Nested(
        BackgroundJobSnapshot, description="The attributes of the background job"
    )
