#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt

from marshmallow_oneofschema import OneOfSchema

from cmk.utils.livestatus_helpers import tables

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.livestatus_utils.commands.acknowledgments import (
    acknowledge_host_problem,
    acknowledge_hostgroup_problem,
)
from cmk.gui.livestatus_utils.commands.downtimes import schedule_servicegroup_service_downtime
from cmk.gui.openapi.utils import param_description

from cmk import fields


class ViaSpecificHost(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="Select a specific host.",
        enum=["host"],
        example="host",
    )
    host_name = gui_fields.HostField(
        description="The name of the host.",
        should_exist=True,
        should_be_monitored=True,
        example="example.com",
        required=True,
    )


class ViaHostGroup(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="Select all hosts in a host group.",
        enum=["hostgroup"],
        example="hostgroup",
    )
    hostgroup_name = gui_fields.GroupField(
        group_type="host",
        example="Servers",
        required=True,
        should_exist=True,
        should_be_monitored=True,
        description=param_description(acknowledge_hostgroup_problem.__doc__, "hostgroup_name"),
    )


class ViaHostQuery(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="Select hosts with a query.",
        enum=["host_by_query"],
        example="host_by_query",
    )
    query = gui_fields.query_field(tables.Hosts, required=True)


class ViaSpecificService(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="Select a specific service on a host.",
        enum=["service"],
        example="service",
    )
    host_name = gui_fields.HostField(
        description="The name of the host.",
        should_exist=True,
        should_be_monitored=True,
        required=True,
    )
    service_description = fields.String(
        description="The acknowledgement process will be applied to all matching service names",
        example="CPU load",
        required=True,
    )


class ViaServiceGroup(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="Select all services in a service group.",
        enum=["servicegroup"],
        example="servicegroup",
    )
    servicegroup_name = gui_fields.GroupField(
        group_type="service",
        example="windows",
        required=True,
        should_exist=True,
        should_be_monitored=True,
        description=param_description(
            schedule_servicegroup_service_downtime.__doc__, "servicegroup_name"
        ),
    )


class ViaServiceQuery(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="Select services with a query.",
        enum=["service_by_query"],
        example="service_by_query",
    )
    query = gui_fields.query_field(
        tables.Services,
        required=True,
        example='{"op": "=", "left": "description", "right": "Service description"}',
    )


class AcknowledgeProblemBase(BaseSchema):
    # NOTE: the docstring param descriptions are generalized for both host and service problems.

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

    expire_on = fields.AwareDateTime(
        required=False,
        default_timezone=dt.UTC,
        example="2025-05-20T07:30:00Z",
        description=(
            str(param_description(acknowledge_host_problem.__doc__, "expire_on"))
            + " The timezone will default to UTC."
        ),
    )


class AcknowledgeHostProblem(ViaSpecificHost, AcknowledgeProblemBase):
    pass


class AcknowledgeHostGroupProblem(ViaHostGroup, AcknowledgeProblemBase):
    pass


class AcknowledgeHostQueryProblem(ViaHostQuery, AcknowledgeProblemBase):
    pass


class AcknowledgeHostRelatedProblem(OneOfSchema):
    type_field = "acknowledge_type"
    type_field_remove = False
    type_schemas = {
        "host": AcknowledgeHostProblem,
        "hostgroup": AcknowledgeHostGroupProblem,
        "host_by_query": AcknowledgeHostQueryProblem,
    }


class AcknowledgeSpecificServiceProblem(ViaSpecificService, AcknowledgeProblemBase):
    pass


class AcknowledgeServiceGroupProblem(ViaServiceGroup, AcknowledgeProblemBase):
    pass


class AcknowledgeServiceQueryProblem(ViaServiceQuery, AcknowledgeProblemBase):
    pass


class AcknowledgeServiceRelatedProblem(OneOfSchema):
    type_field = "acknowledge_type"
    type_field_remove = False
    type_schemas = {
        "service": AcknowledgeSpecificServiceProblem,
        "servicegroup": AcknowledgeServiceGroupProblem,
        "service_by_query": AcknowledgeServiceQueryProblem,
    }


class RemoveProblemAcknowledgement(OneOfSchema):
    type_field = "acknowledge_type"
    type_field_remove = False
    type_schemas = {
        "host": ViaSpecificHost,
        "hostgroup": ViaHostGroup,
        "host_by_query": ViaHostQuery,
        "service": ViaSpecificService,
        "servicegroup": ViaServiceGroup,
        "service_by_query": ViaServiceQuery,
    }
