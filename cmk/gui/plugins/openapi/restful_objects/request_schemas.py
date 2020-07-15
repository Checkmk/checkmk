#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow import Schema, fields  # type: ignore[import]

from cmk.gui.plugins.openapi.utils import param_description
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME_REGEXP
from cmk.gui.plugins.openapi.livestatus_helpers.commands.acknowledgments import \
    acknowledge_host_problem, acknowledge_service_problem


class InputAttribute(Schema):
    key = fields.String(required=True)
    value = fields.String(required=True)


HOST_FIELD = fields.String(
    description="The hostname or IP address itself.",
    required=True,
    pattern=HOST_NAME_REGEXP,
    example="example.com",
)


class CreateHost(Schema):
    """Creating a new host

    Required arguments:

      * `host_name` - A host name with or without domain part. IP addresses are also allowed.
      * `folder` - The folder identifier.

    Optional arguments:

      * `attributes`
      * `nodes`
    """
    host_name = HOST_FIELD
    folder = fields.String(
        description=("The folder-id of the folder under which this folder shall be created. May be "
                     "'root' for the root-folder."),
        pattern="[a-fA-F0-9]{32}|root",
        example="root",
        required=True,
    )
    attributes = fields.Dict(example={})
    nodes = fields.List(fields.String(),
                        description="Nodes where the newly created host should be the "
                        "cluster-container of.",
                        required=False,
                        example=["host1", "host2", "host3"])


class UpdateHost(Schema):
    """Updating of a host

    Only the `attributes` and `nodes` values may be changed.

    Required attributes:

      * none

    Optional arguments:

      * `attributes`
      * `nodes`
    """
    attributes = fields.Dict(example={})
    nodes = fields.List(fields.String(pattern="foo"), example=["host1", "host2", "host3"])


class InputHostGroup(Schema):
    """Creating a host group"""
    name = fields.String(required=True, example="windows")
    alias = fields.String(example="Windows Servers")


class InputContactGroup(Schema):
    """Creating a contact group"""
    name = fields.String(required=True, example="OnCall")
    alias = fields.String(example="Not on Sundays.")


class InputServiceGroup(Schema):
    """Creating a service group"""
    name = fields.String(required=True, example="environment")
    alias = fields.String(example="Environment Sensors")


class CreateFolder(Schema):
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


class UpdateFolder(Schema):
    """Updating a folder"""
    title = fields.String(required=True, example="Virtual Servers.")
    attributes = fields.List(fields.Nested(InputAttribute),
                             example=[{
                                 'key': 'foo',
                                 'value': 'bar'
                             }])


class CreateDowntime(Schema):
    service_description = fields.String(required=False, example="CPU utilization")
    host_name = HOST_FIELD
    end_time = fields.String(
        required=True,
        example="2017-07-21T17:32:28Z",
        description=
        "The end datetime of the new downtime. The format underlies the ISO 8601 profile",
        format="date-time")
    start_time = fields.String(
        required=True,
        example="2017-07-21T17:32:28Z",
        description=
        "The start datetime of the new downtime. The format underlies the ISO 8601 profile",
        format="date-time")
    recurring_option = fields.String(
        required=False,
        pattern="hour|day|week|second week|fourth week|same weekday|same day of the month",
        description=
        "Option when want to repeat this downtime on a regular basis (This only works when using CMC)",
        example="hour")
    delayed_duration = fields.Integer(
        required=False,
        description="With this option the scheduled downtime does not begin automatically at a "
        "nominated time, rather first when a real Problem status appears for the host."
        "In consequence, the start/end time is only the time window in which the scheduled "
        "downtime can begin. The concerning duration is specified in seconds.",
        example=3600)
    comment = fields.String(required=False, example="Security updates")


class AcknowledgeHostProblem(Schema):
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


class AcknowledgeServiceProblem(Schema):
    sticky = fields.Boolean(
        required=False,
        example=False,
        description=param_description(acknowledge_service_problem.__doc__, 'sticky'),
    )

    persistent = fields.Boolean(
        required=False,
        example=False,
        description=param_description(acknowledge_service_problem.__doc__, 'persistent'),
    )

    notify = fields.Boolean(
        required=False,
        example=False,
        description=param_description(acknowledge_service_problem.__doc__, 'notify'),
    )

    comment = fields.String(
        required=False,
        example='This was expected.',
        description=param_description(acknowledge_service_problem.__doc__, 'comment'),
    )
