#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from marshmallow_oneofschema import OneOfSchema

from cmk.utils.livestatus_helpers import tables

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.livestatus_utils.commands.downtimes import (
    schedule_host_downtime,
    schedule_hostgroup_host_downtime,
    schedule_service_downtime,
    schedule_servicegroup_service_downtime,
)
from cmk.gui.plugins.openapi.utils import param_description

from cmk import fields

MONITORED_HOST = gui_fields.HostField(
    description="The hostname or IP address itself.",
    example="example.com",
    should_exist=None,
    should_be_monitored=True,
    required=True,
)

SERVICE_DESCRIPTION_FIELD = fields.String(
    required=False,
    example="CPU utilization",
)

HOST_DURATION = fields.Integer(
    required=False,
    description=param_description(schedule_host_downtime.__doc__, "duration"),
    example=60,
    load_default=0,
)

SERVICE_DURATION = fields.Integer(
    required=False,
    description=param_description(schedule_service_downtime.__doc__, "duration"),
    example=60,
    load_default=0,
)

INCLUDE_ALL_SERVICES = fields.Boolean(
    description="If set, downtimes for all services associated with the given host will be scheduled.",
    required=False,
    load_default=False,
    example=True,
)


class CreateDowntimeBase(BaseSchema):
    start_time = fields.DateTime(
        format="iso8601",
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The start datetime of the new downtime. The format has to conform to the ISO 8601 profile",
    )
    end_time = fields.DateTime(
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The end datetime of the new downtime. The format has to conform to the ISO 8601 profile",
        format="iso8601",
    )
    recur = fields.String(
        required=False,
        enum=[
            "fixed",
            "hour",
            "day",
            "week",
            "second_week",
            "fourth_week",
            "weekday_start",
            "weekday_end",
            "day_of_month",
        ],
        description=param_description(schedule_host_downtime.__doc__, "recur"),
        example="hour",
        load_default="fixed",
    )
    duration = fields.Integer(
        required=False,
        description=param_description(schedule_host_downtime.__doc__, "duration"),
        example=60,
        load_default=0,
    )
    comment = fields.String(required=False, example="Security updates")


class CreateHostDowntimeBase(CreateDowntimeBase):
    downtime_type = fields.String(
        required=True,
        description="The type of downtime to create.",
        enum=["host", "hostgroup", "host_by_query"],
        example="host",
    )


class CreateServiceDowntimeBase(CreateDowntimeBase):
    downtime_type = fields.String(
        required=True,
        description="The type of downtime to create.",
        enum=["service", "servicegroup", "service_by_query"],
        example="service",
    )


class CreateHostDowntime(CreateHostDowntimeBase):
    host_name = MONITORED_HOST
    duration = HOST_DURATION


class CreateServiceDowntime(CreateServiceDowntimeBase):
    # We rely on the code in the endpoint itself to check if the host is there or not.
    # Here, we don't want to 403 when the host is inaccessible to the user,
    # but the specific service on that host can be accessed.
    host_name = gui_fields.HostField(should_exist=None)
    service_descriptions = fields.List(
        fields.String(),
        uniqueItems=True,
        required=True,
        example=["CPU utilization", "Memory"],
        description=param_description(schedule_service_downtime.__doc__, "service_description"),
    )
    duration = fields.Integer(
        required=False,
        description=param_description(schedule_service_downtime.__doc__, "duration"),
        example=60,
        load_default=0,
    )


class CreateServiceGroupDowntime(CreateServiceDowntimeBase):
    servicegroup_name = gui_fields.GroupField(
        group_type="service",
        example="windows",
        required=True,
        description=param_description(
            schedule_servicegroup_service_downtime.__doc__, "servicegroup_name"
        ),
    )
    duration = HOST_DURATION


class CreateHostGroupDowntime(CreateHostDowntimeBase):
    hostgroup_name = gui_fields.GroupField(
        group_type="host",
        example="windows",
        required=True,
        description=param_description(schedule_hostgroup_host_downtime.__doc__, "hostgroup_name"),
        should_exist=True,
    )
    duration = HOST_DURATION


class CreateHostQueryDowntime(CreateHostDowntimeBase):
    query = gui_fields.query_field(tables.Hosts, required=True)
    duration = HOST_DURATION


class CreateServiceQueryDowntime(CreateServiceDowntimeBase):
    query = gui_fields.query_field(tables.Services, required=True)
    duration = SERVICE_DURATION


class CreateHostRelatedDowntime(OneOfSchema):
    type_field = "downtime_type"
    type_field_remove = False
    type_schemas = {
        "host": CreateHostDowntime,
        "hostgroup": CreateHostGroupDowntime,
        "host_by_query": CreateHostQueryDowntime,
    }


class CreateServiceRelatedDowntime(OneOfSchema):
    type_field = "downtime_type"
    type_field_remove = False
    type_schemas = {
        "service": CreateServiceDowntime,
        "servicegroup": CreateServiceGroupDowntime,
        "service_by_query": CreateServiceQueryDowntime,
    }


class DeleteDowntimeBase(BaseSchema):
    delete_type = fields.String(
        required=True,
        description="The option how to delete a downtime.",
        enum=["params", "query", "by_id"],
        example="params",
    )


class DeleteDowntimeById(DeleteDowntimeBase):
    downtime_id = fields.String(
        description="The id of the downtime",
        example="54",
        required=True,
    )


class DeleteDowntimeByName(DeleteDowntimeBase):
    host_name = gui_fields.HostField(
        required=True,
        should_exist=None,  # we don't care
        description="If set alone, then all downtimes of the host will be removed.",
        example="example.com",
    )
    service_descriptions = fields.List(
        SERVICE_DESCRIPTION_FIELD,
        description="If set, the downtimes of the listed services of the specified host will be "
        "removed. If a service has multiple downtimes then all will be removed",
        required=False,
        example=["CPU load", "Memory"],
    )


class DeleteDowntimeByQuery(DeleteDowntimeBase):
    query = gui_fields.query_field(tables.Downtimes, required=True)


class DeleteDowntime(OneOfSchema):
    type_field = "delete_type"
    type_field_remove = False
    type_schemas = {
        "by_id": DeleteDowntimeById,
        "params": DeleteDowntimeByName,
        "query": DeleteDowntimeByQuery,
    }


class BulkDeleteDowntime(BaseSchema):
    host_name = MONITORED_HOST
    entries = fields.List(
        fields.Integer(
            required=True,
            description="The id for either a host downtime or service downtime",
            example=1120,
        ),
        required=True,
        example=[1120, 1121],
        description="A list of downtime ids.",
    )
