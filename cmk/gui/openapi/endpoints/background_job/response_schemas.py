#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.fields.base import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject

from cmk import fields


class BackgroundJobStatus(BaseSchema):
    # TODO add more fields
    state = fields.String(
        required=True,
        description="The state of the background job",
        example="finished",
    )


class BackgroundJobSnapshot(BaseSchema):
    # TODO add more fields
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
