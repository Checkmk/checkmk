#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from marshmallow_oneofschema import OneOfSchema

from cmk.gui.fields import HostField
from cmk.gui.fields.base import BaseSchema
from cmk.gui.plugins.openapi.endpoints.sla.common import CustomTimeRange, PreDefinedTimeRange

from cmk import fields


class TimeRange(OneOfSchema):
    type_field = "range_type"
    type_field_remove = False
    type_schemas = {
        "pre_defined": PreDefinedTimeRange,
        "custom": CustomTimeRange,
    }


class Service(BaseSchema):
    host_name = HostField(
        required=True,
        should_exist=True,
    )
    service_description = fields.String(
        description="The service whose SLA data is to be computed.",
        example="CPU load",
        required=True,
    )


class SLAComputeTarget(BaseSchema):
    sla_ids = fields.List(
        fields.String,
        description="The ids of the SLA configurations for which the SLA should be computed.",
        example=["sla_configuration_1", "sla_configuration_2"],
        required=True,
    )
    time_ranges = fields.List(
        fields.Nested(TimeRange),
        description="The time ranges for which the SLA should be computed.",
        example=[{"range_type": "pre_defined", "range": "today"}],
        required=True,
    )
    services = fields.List(
        fields.Nested(Service),
        description="The services for which the SLA should be computed.",
        example=[{"host_name": "heute", "service_description": "CPU load"}],
        required=True,
    )


class SLAComputeRequest(BaseSchema):
    sla_compute_targets = fields.List(
        fields.Nested(SLAComputeTarget),
        description="The SLA compute targets for which the SLA should be computed.",
        required=True,
        example=[
            {
                "sla_ids": ["sla_configuration_1"],
                "time_ranges": [{"range_type": "pre_defined", "range": "today"}],
                "services": [{"host_name": "heute", "service_description": "CPU load"}],
            }
        ],
    )
