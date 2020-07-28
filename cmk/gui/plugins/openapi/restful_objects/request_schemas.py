#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.livestatus_helpers.commands.downtimes import (
    schedule_host_downtime,
    schedule_hostgroup_host_downtime,
    schedule_service_downtime,
    schedule_servicegroup_service_downtime,
)
from cmk.gui.plugins.openapi.utils import param_description, BaseSchema
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME_REGEXP
from cmk.gui.plugins.openapi.livestatus_helpers.commands.acknowledgments import \
    acknowledge_host_problem, acknowledge_service_problem


class InputAttribute(BaseSchema):
    key = fields.String(required=True)
    value = fields.String(required=True)


HOST_FIELD = fields.String(
    description="The hostname or IP address itself.",
    required=True,
    pattern=HOST_NAME_REGEXP,
    example="example.com",
)

FOLDER_FIELD = fields.String(
    description=("The folder-id of the folder under which this folder shall be created. May be "
                 "'root' for the root-folder."),
    pattern="[a-fA-F0-9]{32}|root",
    example="root",
    required=True,
)


class CreateHost(BaseSchema):
    """Creating a new host

    Required arguments:

      * `host_name` - A host name with or without domain part. IP addresses are also allowed.
      * `folder` - The folder identifier.

    Optional arguments:

      * `attributes`
      * `nodes`
    """
    host_name = HOST_FIELD
    folder = FOLDER_FIELD
    attributes = fields.Dict(example={'ipaddress': '192.168.0.123'})
    nodes = fields.List(fields.String(),
                        description="Nodes where the newly created host should be the "
                        "cluster-container of.",
                        required=False,
                        example=["host1", "host2", "host3"])


class BulkCreateHost(BaseSchema):
    entries = fields.List(
        fields.Nested(CreateHost),
        example=[{
            "host_name": "example.com",
            "folder": "root",
            "attributes": {},
            "nodes": ["host1", "host2"],
        }],
        uniqueItems=True,
    )


class UpdateHost(BaseSchema):
    """Updating of a host

    Only the `attributes` and `nodes` values may be changed.

    Required attributes:

      * none

    Optional arguments:

      * `attributes`
      * `nodes`
    """
    attributes = fields.Dict(example={})
    nodes = fields.List(HOST_FIELD, example=["host1", "host2", "host3"])


class InputHostGroup(BaseSchema):
    """Creating a host group"""
    name = fields.String(required=True, example="windows")
    alias = fields.String(example="Windows Servers")


class BulkInputHostGroup(BaseSchema):
    """Bulk creating host groups"""
    entries = fields.List(
        fields.Nested(InputHostGroup),
        example=[{
            'name': 'windows',
            'alias': 'Windows Servers',
        }],
        uniqueItems=True,
    )


class InputContactGroup(BaseSchema):
    """Creating a contact group"""
    name = fields.String(required=True, example="OnCall")
    alias = fields.String(example="Not on Sundays.")


class InputServiceGroup(BaseSchema):
    """Creating a service group"""
    name = fields.String(required=True, example="environment")
    alias = fields.String(example="Environment Sensors")


class CreateFolder(BaseSchema):
    """Creating a folder

    Every folder needs a parent folder to reside in. The uppermost folder is called the "root"
    Folder and has the fixed identifier "root".

    Parameters:

     * `name` is the actual folder-name on disk.
     * `title` is meant for humans to read.
     * `parent` is the identifier for the parent-folder. This identifier stays the same,
        even if the parent folder is being moved.
     * `attributes` can hold special configuration parameters which control various aspects of
        the monitoring system. Most of these attributes will be inherited by hosts within that
        folder. For more information please have a look at the
        [Host Administration chapter of the handbook](https://checkmk.com/cms_wato_hosts.html#Introduction).
    """
    name = fields.String(description="The name of the folder.", required=True, example="production")
    title = fields.String(
        required=True,
        example="Production Hosts",
    )
    parent = fields.String(
        description=("The folder-id of the folder under which this folder shall be created. May be "
                     "'root' for the root-folder."),
        pattern="[a-fA-F0-9]{32}|root",
        example="root",
        required=True,
    )
    attributes = fields.Dict(example={'foo': 'bar'})


class BulkCreateFolder(BaseSchema):
    entries = fields.List(
        fields.Nested(CreateFolder),
        example=[{
            "name": "production",
            "parent": "root",
            "attributes": {
                "foo": "bar"
            },
        }],
        uniqueItems=True,
    )


class UpdateFolder(BaseSchema):
    """Updating a folder"""
    title = fields.String(required=True, example="Virtual Servers.")
    attributes = fields.List(fields.Nested(InputAttribute),
                             example=[{
                                 'key': 'foo',
                                 'value': 'bar'
                             }])


class CreateDowntimeBase(BaseSchema):
    downtime_type = fields.String(
        required=True,
        description="The type of downtime to create.",
        enum=['host', 'service', 'hostgroup', 'servicegroup'],
        example="host",
    )
    start_time = fields.DateTime(
        format="iso8601",
        required=True,
        example="2017-07-21T17:32:28Z",
        description=
        "The start datetime of the new downtime. The format has to conform to the ISO 8601 profile",
    )
    end_time = fields.DateTime(
        required=True,
        example="2017-07-21T17:32:28Z",
        description=
        "The end datetime of the new downtime. The format has to conform to the ISO 8601 profile",
        format="iso8601",
    )
    recur = fields.String(
        required=False,
        enum=[
            "fixed", "hour", "day", "week", "second_week", "fourth_week", "weekday_start",
            "weekday_end", "day_of_month"
        ],
        description=param_description(schedule_host_downtime.__doc__, 'recur'),
        example="hour",
        missing="fixed",
    )
    duration = fields.Integer(
        required=False,
        description=param_description(schedule_host_downtime.__doc__, 'duration'),
        example=3600,
        missing=0,
    )
    comment = fields.String(required=False, example="Security updates")


SERVICE_DESCRIPTION_FIELD = fields.String(required=False, example="CPU utilization")

HOST_DURATION = fields.Integer(
    required=False,
    description=param_description(schedule_host_downtime.__doc__, 'duration'),
    example=3600,
    missing=0,
)


class CreateHostDowntime(CreateDowntimeBase):
    host_name = HOST_FIELD
    duration = HOST_DURATION
    include_all_services = fields.Boolean(
        required=False,
        description=param_description(schedule_host_downtime.__doc__, 'include_all_services'),
        example=False,
        missing=False,
    )


class CreateServiceDowntime(CreateDowntimeBase):
    host_name = HOST_FIELD
    service_descriptions = fields.List(
        fields.String(),
        uniqueItems=True,
        required=True,
        example=["CPU utilization", "Memory"],
        description=param_description(schedule_service_downtime.__doc__, 'service_description'),
    )
    duration = fields.Integer(
        required=False,
        description=param_description(schedule_service_downtime.__doc__, 'duration'),
        example=3600,
        missing=0,
    )


class CreateServiceGroupDowntime(CreateDowntimeBase):
    servicegroup_name = fields.String(
        required=True,
        description=param_description(schedule_servicegroup_service_downtime.__doc__,
                                      'servicegroup_name'),
        example='Webservers',
    )
    include_hosts = fields.Boolean(
        required=False,
        description=param_description(schedule_servicegroup_service_downtime.__doc__,
                                      'include_hosts'),
        example=False,
        missing=False,
    )
    duration = HOST_DURATION


class CreateHostGroupDowntime(CreateDowntimeBase):
    hostgroup_name = fields.String(
        required=True,
        description=param_description(schedule_hostgroup_host_downtime.__doc__, 'hostgroup_name'),
        example='Servers',
    )
    include_all_services = fields.Boolean(
        required=False,
        description=param_description(schedule_hostgroup_host_downtime.__doc__,
                                      'include_all_services'),
        example=False,
        missing=False,
    )
    duration = HOST_DURATION


class CreateDowntime(OneOfSchema):
    type_field = 'downtime_type'
    type_field_remove = False
    type_schemas = {
        'host': CreateHostDowntime,
        'hostgroup': CreateHostGroupDowntime,
        'service': CreateServiceDowntime,
        'servicegroup': CreateServiceGroupDowntime,
    }


class AcknowledgeHostProblem(BaseSchema):
    sticky = fields.Boolean(
        required=False,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, 'sticky'),
    )

    persistent = fields.Boolean(
        required=False,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, 'persistent'),
    )

    notify = fields.Boolean(
        required=False,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, 'notify'),
    )

    comment = fields.String(
        required=False,
        example='This was expected.',
        description=param_description(acknowledge_host_problem.__doc__, 'comment'),
    )


class BulkAcknowledgeHostProblem(AcknowledgeHostProblem):
    entries = fields.List(
        HOST_FIELD,
        required=True,
        example=["example.com", "sample.com"],
    )


SERVICE_STICKY_FIELD = fields.Boolean(
    required=False,
    example=False,
    description=param_description(acknowledge_service_problem.__doc__, 'sticky'),
)

SERVICE_PERSISTENT_FIELD = fields.Boolean(
    required=False,
    example=False,
    description=param_description(acknowledge_service_problem.__doc__, 'persistent'),
)

SERVICE_NOTIFY_FIELD = fields.Boolean(
    required=False,
    example=False,
    description=param_description(acknowledge_service_problem.__doc__, 'notify'),
)

SERVICE_COMMENT_FIELD = fields.String(
    required=False,
    example='This was expected.',
    description=param_description(acknowledge_service_problem.__doc__, 'comment'),
)


class AcknowledgeServiceProblem(BaseSchema):
    sticky = SERVICE_STICKY_FIELD
    persistent = SERVICE_PERSISTENT_FIELD
    notify = SERVICE_NOTIFY_FIELD
    comment = SERVICE_COMMENT_FIELD


class BulkAcknowledgeServiceProblem(AcknowledgeServiceProblem):
    host_name = HOST_FIELD
    entries = fields.List(
        SERVICE_DESCRIPTION_FIELD,
        required=True,
        example=["CPU utilization", "Memory"],
    )


class BulkDeleteDowntime(BaseSchema):
    host_name = HOST_FIELD
    entries = fields.List(
        fields.Integer(
            required=True,
            description="The id for either a host downtime or service downtime",
            example=1120,
        ),
        required=True,
        example=[1120, 1121],
    )


class BulkDeleteHost(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        HOST_FIELD,
        required=True,
        example=["example", "sample"],
    )


class BulkDeleteFolder(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        FOLDER_FIELD,
        required=True,
        example=["production", "secondproduction"],
    )


class BulkDeleteHostGroup(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the host group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
    )


class BulkDeleteServiceGroup(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the service group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
    )


class BulkDeleteContactGroup(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the contact group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
    )
