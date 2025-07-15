#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from marshmallow import post_load, ValidationError
from marshmallow_oneofschema import OneOfSchema

from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.livestatus_utils.commands.downtimes import (
    schedule_host_downtime,
    schedule_hostgroup_host_downtime,
    schedule_service_downtime,
    schedule_servicegroup_service_downtime,
)
from cmk.gui.livestatus_utils.commands.utils import to_timestamp
from cmk.gui.openapi.utils import param_description
from cmk.utils.livestatus_helpers import tables

MONITORED_HOST = gui_fields.HostField(
    description="The host name or IP address itself.",
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

DOWNTIME_ID = fields.String(
    description="The id of the downtime",
    example="54",
    required=True,
)


class NonZeroInteger(fields.Integer):
    def _validate(self, value: Any) -> None:
        if value == 0:
            raise ValidationError("The value cannot be zero.")


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
        enum=["host", "hostgroup", "host_by_query"],
        example="host",
        description=(
            "The type of downtime to create.\n\n"
            "Valid options are:\n\n"
            " * `host` - Schedule downtimes for a host identified by host name or IP address\n"
            " * `hostgroup` - Schedule downtimes for all hosts belonging to the specified hostgroup\n"
            " * `host_by_query` - Schedule downtimes for all host matching the query\n"
        ),
    )


class CreateServiceDowntimeBase(CreateDowntimeBase):
    downtime_type = fields.String(
        required=True,
        enum=["service", "servicegroup", "service_by_query"],
        example="service",
        description=(
            "The type of downtime to create.\n\n"
            "Valid options are:\n\n"
            " * `service` - Schedule downtimes for services whose names are listed in service_descriptions and belongs to the host identified by name or IP address in host_name.\n"
            " * `servicegroup` - Schedule downtimes for all services in a given service group\n"
            " * `service_by_query` - Schedule downtimes for services matching the query\n"
        ),
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
    query = gui_fields.query_field(
        tables.Services,
        required=True,
        example='{"op": "=", "left": "description", "right": "Service description"}',
    )
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
        enum=["params", "query", "by_id", "hostgroup", "servicegroup"],
        example="params",
    )


class DeleteDowntimeById(DeleteDowntimeBase):
    site_id = gui_fields.SiteField(
        description="The site from which you want to delete a downtime.",
        example="heute",
        presence="should_exist",
        required=True,
    )
    downtime_id = DOWNTIME_ID


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
    query = gui_fields.query_field(
        tables.Downtimes,
        required=True,
        example='{"op": "=", "left": "host_name", "right": "example.com"}',
    )


class DeleteDowntimeByHostGroup(DeleteDowntimeBase):
    hostgroup_name = gui_fields.GroupField(
        group_type="host",
        required=True,
        should_exist=True,
        description="Name of a valid hostgroup, all current downtimes for hosts in this group will be deleted.",
        example="windows",
    )


class DeleteDowntimeByServiceGroup(DeleteDowntimeBase):
    servicegroup_name = gui_fields.GroupField(
        group_type="service",
        required=True,
        should_exist=True,
        description="Name of a valid servicegroup, all current downtimes for services in this group will be deleted.",
        example="windows",
    )


class DeleteDowntime(OneOfSchema):
    type_field = "delete_type"
    type_field_remove = False
    type_schemas = {
        "by_id": DeleteDowntimeById,
        "params": DeleteDowntimeByName,
        "query": DeleteDowntimeByQuery,
        "hostgroup": DeleteDowntimeByHostGroup,
        "servicegroup": DeleteDowntimeByServiceGroup,
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


class ModifyEndTimeBaseSchema(BaseSchema):
    modify_type = fields.String(
        required=False,
        description="How to modify the end time of a downtime.",
        enum=["absolute", "relative"],
        example="absolute",
    )


class ModifyEndTimeByDatetime(ModifyEndTimeBaseSchema):
    value = fields.DateTime(
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The end datetime of the downtime. The format has to conform to the ISO 8601 profile",
        format="iso8601",
    )

    @post_load
    def prefix_value(self, data, **kwargs):
        data["value"] = str(to_timestamp(data["value"]))
        return data


class ModifyEndTimeByDelta(ModifyEndTimeBaseSchema):
    value = NonZeroInteger(
        required=True,
        description="A positive or negative number representing the amount of minutes to be added to or substracted from the current end time. The value must be non-zero",
        example=60,
    )

    @post_load
    def prefix_value(self, data, **kwargs):
        # Livestatus is expectind seconds, so we convert the minutes to seconds and then add + or - sign
        data["value"] = f"{'+' if data['value'] >= 0 else '-'}{abs(data['value']) * 60}"
        return data


class ModifyEndTimeType(OneOfSchema):
    type_field = "modify_type"
    type_field_remove = False
    type_schemas = {
        "absolute": ModifyEndTimeByDatetime,
        "relative": ModifyEndTimeByDelta,
    }


class ModifyDowntimeFieldsSchema(BaseSchema):
    modify_type = fields.String(
        required=True,
        description="The option of how to select the downtimes to be targeted by the modification.",
        enum=["params", "query", "by_id", "hostgroup", "servicegroup"],
        example="params",
    )

    end_time = fields.Nested(
        ModifyEndTimeType,
        required=False,
        description="The option how to modify the end time of a downtime. If modify_type is set to 'absolute', then the end time will be set to the date time specified in the value field. If modify_type is set to 'relative', then the current end time will be modified by the amount of minutes specified in the value field. If this attribute is not present, then the end time will not be modified.",
        example={"modify_type": "absolute", "value": "2024-03-06T12:00:00Z"},
    )

    comment = fields.String(
        required=False, example="Security updates", description="The comment for the downtime."
    )


class ModifyDowntimeById(ModifyDowntimeFieldsSchema):
    site_id = gui_fields.SiteField(
        description="The site from which you want to modify a downtime.",
        example="central",
        presence="should_exist",
        required=True,
    )
    downtime_id = DOWNTIME_ID


class ModifyDowntimeByQuery(ModifyDowntimeFieldsSchema):
    query = gui_fields.query_field(
        tables.Downtimes,
        required=True,
        example='{"op": "=", "left": "host_name", "right": "example.com"}',
    )


class ModifyDowntimeByName(ModifyDowntimeFieldsSchema):
    host_name = gui_fields.HostField(
        required=True,
        should_exist=None,
        description="If set alone, then all downtimes of the host will be modified.",
        example="example.com",
    )
    service_descriptions = fields.List(
        SERVICE_DESCRIPTION_FIELD,
        description="If set, the downtimes of the listed services of the specified host will be "
        "modified. If a service has multiple downtimes then all will be modified",
        required=False,
        example=["CPU load", "Memory"],
    )


class ModifyDowntimeByHostGroup(ModifyDowntimeFieldsSchema):
    hostgroup_name = gui_fields.GroupField(
        group_type="host",
        required=True,
        should_exist=True,
        description="Name of a valid hostgroup, all current downtimes for hosts in this group will be modified.",
        example="windows",
    )


class ModifyDowntimeByServiceGroup(ModifyDowntimeFieldsSchema):
    servicegroup_name = gui_fields.GroupField(
        group_type="service",
        required=True,
        should_exist=True,
        description="Name of a valid servicegroup, all current downtimes for services in this group will be modified.",
        example="windows",
    )


class ModifyDowntime(OneOfSchema):
    type_field = "modify_type"
    type_field_remove = False
    type_schemas = {
        "by_id": ModifyDowntimeById,
        "params": ModifyDowntimeByName,
        "query": ModifyDowntimeByQuery,
        "hostgroup": ModifyDowntimeByHostGroup,
        "servicegroup": ModifyDowntimeByServiceGroup,
    }
