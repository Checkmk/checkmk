#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow_oneofschema import OneOfSchema

from cmk import fields
from cmk.gui.fields.base import BaseSchema
from cmk.gui.fields.definitions import FolderField, HostField


class PerformanceSettings(BaseSchema):
    responses_timeout = fields.Integer(
        required=False,
        description="Timeout for responses",
        load_default=8,
        example=8,
    )
    hop_probes = fields.Integer(
        required=False,
        description="Number of probes per hop",
        load_default=2,
        example=2,
    )
    max_gateway_distance = fields.Integer(
        required=False,
        description="Maximum distance (TTL) to gateway",
        load_default=10,
        example=10,
    )
    ping_probes = fields.Integer(
        required=False,
        description="Number of ping probes",
        load_default=5,
        example=5,
    )


class Configuration(BaseSchema):
    force_explicit_parents = fields.Boolean(
        required=False,
        description="Force explicit setting for parents even if setting match that of the folder",
        load_default=False,
        example=False,
    )


class GatewayHostOptions(BaseSchema):
    option = fields.String(
        enum=["no_gateway_hosts", "create_in_folder", "create_in_host_location"],
        required=True,
        description="Creation of gateway hosts option",
        example="no_gateway_hosts",
    )


class NoGatewayHosts(GatewayHostOptions):
    pass


GATEWAY_HOSTS_ALIAS = fields.String(
    required=False,
    description="Alias for created gateway hosts",
    load_default="Created by parent scan",
    example="Created by parent scan",
)


class CreateInFolder(GatewayHostOptions):
    folder = FolderField(
        required=True,
        example="/",
        description="Folder location where the gateway hosts should be created",
    )
    hosts_alias = GATEWAY_HOSTS_ALIAS


class CreateInHostLocation(GatewayHostOptions):
    hosts_alias = GATEWAY_HOSTS_ALIAS


class GatewayHosts(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "no_gateway_hosts": NoGatewayHosts,
        "create_in_folder": CreateInFolder,
        "create_in_host_location": CreateInHostLocation,
    }


class ParentScan(BaseSchema):
    host_names = fields.List(
        HostField,
        description="Targeted hosts for parent scan.",
        example=["host1", "host2"],
        validate=len,
        required=True,
    )
    performance = fields.Nested(
        PerformanceSettings,
        required=True,
        description="Parent scan performance related options",
        example={
            "responses_timeout": 8,
            "hop_probes": 2,
            "max_gateway_distance": 10,
            "ping_probes": 5,
        },
    )
    configuration = fields.Nested(
        Configuration,
        required=True,
        description="Parent scan configuration options",
        example={"force_explicit_parents": False},
    )
    gateway_hosts = fields.Nested(
        GatewayHosts,
        required=True,
        description="Creation of gateway hosts options",
        example={"option": "no_gateway_hosts"},
    )
