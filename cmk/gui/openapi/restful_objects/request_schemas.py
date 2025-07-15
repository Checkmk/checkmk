#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.livestatus_utils.commands.acknowledgments import acknowledge_service_problem
from cmk.gui.livestatus_utils.commands.downtimes import schedule_servicegroup_service_downtime
from cmk.gui.openapi.utils import param_description

MONITORED_HOST = gui_fields.HostField(
    description="The host name or IP address itself.",
    example="example.com",
    should_exist=None,
    should_be_monitored=True,
    required=True,
)

SERVICEGROUP_NAME = fields.String(
    required=True,
    description=param_description(
        schedule_servicegroup_service_downtime.__doc__, "servicegroup_name"
    ),
    example="Webservers",
)

SERVICE_DESCRIPTION_FIELD = fields.String(
    required=False,
    example="CPU utilization",
)

AUTH_ENFORCE_PASSWORD_CHANGE = fields.Boolean(
    required=False,
    description="If set to True, the user will be forced to change his password on the next "
    "login or access. Defaults to False",
    example=False,
    load_default=False,
)

SERVICE_STICKY_FIELD = fields.Boolean(
    required=False,
    load_default=False,
    example=False,
    description=param_description(acknowledge_service_problem.__doc__, "sticky"),
)

SERVICE_PERSISTENT_FIELD = fields.Boolean(
    required=False,
    load_default=False,
    example=False,
    description=param_description(acknowledge_service_problem.__doc__, "persistent"),
)

SERVICE_NOTIFY_FIELD = fields.Boolean(
    required=False,
    load_default=False,
    example=False,
    description=param_description(acknowledge_service_problem.__doc__, "notify"),
)

SERVICE_COMMENT_FIELD = fields.String(
    required=False,
    load_default="Acknowledged",
    example="This was expected.",
    description=param_description(acknowledge_service_problem.__doc__, "comment"),
)


class AcknowledgeServiceProblem(BaseSchema):
    sticky = SERVICE_STICKY_FIELD
    persistent = SERVICE_PERSISTENT_FIELD
    notify = SERVICE_NOTIFY_FIELD
    comment = SERVICE_COMMENT_FIELD


class BulkAcknowledgeServiceProblem(AcknowledgeServiceProblem):
    host_name = MONITORED_HOST
    entries = fields.List(
        SERVICE_DESCRIPTION_FIELD,
        required=True,
        example=["CPU utilization", "Memory"],
    )
