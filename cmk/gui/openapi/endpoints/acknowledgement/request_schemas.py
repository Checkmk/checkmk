#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from marshmallow_oneofschema import OneOfSchema

from cmk.utils.livestatus_helpers import tables

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.livestatus_utils.commands.acknowledgments import (
    acknowledge_host_problem,
    acknowledge_hostgroup_problem,
    acknowledge_service_problem,
)
from cmk.gui.livestatus_utils.commands.downtimes import schedule_servicegroup_service_downtime
from cmk.gui.openapi.utils import param_description

from cmk import fields


class AcknowledgeHostProblemBase(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="The acknowledge host selection type.",
        enum=["host", "hostgroup", "host_by_query"],
        example="host",
    )
    sticky = fields.Boolean(
        required=False,
        load_default=True,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, "sticky"),
    )

    persistent = fields.Boolean(
        required=False,
        load_default=False,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, "persistent"),
    )

    notify = fields.Boolean(
        required=False,
        load_default=True,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, "notify"),
    )

    comment = fields.String(
        required=True,
        example="This was expected.",
        description=param_description(acknowledge_host_problem.__doc__, "comment"),
    )


class AcknowledgeHostProblem(AcknowledgeHostProblemBase):
    host_name = gui_fields.HostField(
        description="The name of the host.",
        should_exist=True,
        should_be_monitored=True,
        example="example.com",
        required=True,
    )


class AcknowledgeHostGroupProblem(AcknowledgeHostProblemBase):
    hostgroup_name = gui_fields.GroupField(
        group_type="host",
        example="Servers",
        required=True,
        should_exist=True,
        should_be_monitored=True,
        description=param_description(acknowledge_hostgroup_problem.__doc__, "hostgroup_name"),
    )


class AcknowledgeHostQueryProblem(AcknowledgeHostProblemBase):
    query = gui_fields.query_field(tables.Hosts, required=True)


class AcknowledgeHostRelatedProblem(OneOfSchema):
    type_field = "acknowledge_type"
    type_field_remove = False
    type_schemas = {
        "host": AcknowledgeHostProblem,
        "hostgroup": AcknowledgeHostGroupProblem,
        "host_by_query": AcknowledgeHostQueryProblem,
    }


class AcknowledgeServiceProblemBase(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="The acknowledge service selection type.",
        enum=["service", "servicegroup", "service_by_query"],
        example="service",
    )

    sticky = fields.Boolean(
        required=False,
        load_default=True,
        example=False,
        description=param_description(acknowledge_service_problem.__doc__, "sticky"),
    )

    persistent = fields.Boolean(
        required=False,
        load_default=False,
        example=False,
        description=param_description(acknowledge_service_problem.__doc__, "persistent"),
    )

    notify = fields.Boolean(
        required=False,
        load_default=True,
        example=False,
        description=param_description(acknowledge_service_problem.__doc__, "notify"),
    )

    comment = fields.String(
        required=True,
        example="This was expected.",
        description=param_description(acknowledge_service_problem.__doc__, "comment"),
    )


class AcknowledgeSpecificServiceProblem(AcknowledgeServiceProblemBase):
    host_name = gui_fields.HostField(
        should_exist=True,
        should_be_monitored=True,
        required=True,
    )
    service_description = fields.String(
        description="The acknowledgement process will be applied to all matching service names",
        example="CPU load",
        required=True,
    )


class AcknowledgeServiceGroupProblem(AcknowledgeServiceProblemBase):
    servicegroup_name = gui_fields.GroupField(
        group_type="service",
        example="windows",
        required=True,
        description=param_description(
            schedule_servicegroup_service_downtime.__doc__, "servicegroup_name"
        ),
    )


class AcknowledgeServiceQueryProblem(AcknowledgeServiceProblemBase):
    query = gui_fields.query_field(
        tables.Services,
        required=True,
        example='{"op": "=", "left": "description", "right": "Service description"}',
    )


class AcknowledgeServiceRelatedProblem(OneOfSchema):
    type_field = "acknowledge_type"
    type_field_remove = False
    type_schemas = {
        "service": AcknowledgeSpecificServiceProblem,
        "servicegroup": AcknowledgeServiceGroupProblem,
        "service_by_query": AcknowledgeServiceQueryProblem,
    }
