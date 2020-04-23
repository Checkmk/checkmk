#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow import Schema, fields  # type: ignore[import]

HOSTNAME_REGEXP = '[-0-9a-zA-Z_.]+'


class InputAttribute(Schema):
    key = fields.String(required=True)
    value = fields.String(required=True)


class CreateHost(Schema):
    """Creating a new host

    Required arguments:

      * `hostname` - A host name with or without domain part. IP addresses are also allowed.
      * `folder` - The folder identifier.

    Optional arguments:

      * `attributes`
      * `nodes`
    """
    hostname = fields.String(
        description="The hostname or IP address itself.",
        required=True,
        pattern=HOSTNAME_REGEXP,
        example="example.com",
    )
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
