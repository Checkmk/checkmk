#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow import Schema, fields  # type: ignore[import]


class InputAttribute(Schema):
    key = fields.String(required=True)
    value = fields.String(required=True)


class CreateHost(Schema):
    """Schema for creating a new host"""
    hostname = fields.String(
        description="The hostname itself. Only characters valid in FQDNs are allowed.",
        required=True,
        pattern='[a-zA-Z][a-zA-Z-]+',
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
    attributes = fields.Dict(example={})
    nodes = fields.List(fields.String(), example=["host1", "host2", "host3"])


class InputHostGroup(Schema):
    name = fields.String(required=True, example="windows")
    alias = fields.String(example="Windows Servers")


class InputContactGroup(Schema):
    """InputContactGroup

    Schema for submitting Contact Group information."""
    name = fields.String(required=True, example="OnCall")
    alias = fields.String(example="Not on Sundays.")


class InputServiceGroup(Schema):
    name = fields.String(required=True, example="environment")
    alias = fields.String(example="Environment Sensors")


class InputFolder(Schema):
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
    title = fields.String(required=True, example="Virtual Servers.")
    attributes = fields.List(fields.Nested(InputAttribute),
                             example=[{
                                 'key': 'foo',
                                 'value': 'bar'
                             }])
