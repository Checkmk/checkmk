#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from marshmallow import post_dump

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import attr_openapi_schema, BaseSchema
from cmk.gui.plugins.openapi.restful_objects.response_schemas import (
    DomainObject,
    DomainObjectCollection,
    FolderSchema,
)

from cmk import fields


class HostExtensionsEffectiveAttributesSchema(attr_openapi_schema("host", "view")):  # type: ignore
    @post_dump(pass_original=True)
    def add_tags_and_custom_attributes_back(
        self, dump_data: dict[str, Any], original_data: dict[str, Any], **_kwargs: Any
    ) -> dict[str, Any]:
        # Custom attributes and tags are thrown away during validation as they have no field in the schema.
        # So we dump them back in here.
        original_data.update(dump_data)
        return original_data


class HostExtensions(BaseSchema):
    folder = gui_fields.FolderField(
        description="The folder, in which this host resides.",
    )
    attributes = gui_fields.host_attributes_field(
        "host",
        "view",
        "outbound",
        description="Attributes of this host.",
        example={"ipaddress": "192.168.0.123"},
    )
    effective_attributes = fields.Nested(
        HostExtensionsEffectiveAttributesSchema(),
        required=False,
        description="All attributes of this host and all parent folders.",
        example={"tag_snmp_ds": None},
    )
    is_cluster = fields.Boolean(
        description="If this is a cluster host, i.e. a container for other hosts.",
    )
    is_offline = fields.Boolean(
        description="Whether the host is offline",
    )
    cluster_nodes = fields.List(
        gui_fields.HostField(),
        allow_none=True,
        load_default=None,
        description="In the case this is a cluster host, these are the cluster nodes.",
    )


class HostMembers(BaseSchema):
    folder_config = fields.Nested(
        FolderSchema(),
        description="The folder in which this host resides. It is represented by a hexadecimal "
        "identifier which is it's 'primary key'. The folder can be accessed via the "
        "`self`-link provided in the links array.",
    )


class HostConfigSchema(DomainObject):
    domainType = fields.Constant(
        "host_config",
        required=True,
        description="The domain type of the object.",
    )
    members = fields.Nested(
        HostMembers,
        description="All the members of the host object.",
    )
    extensions = fields.Nested(
        HostExtensions,
        description="All the data and metadata of this host.",
    )


class HostConfigCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "host_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(HostConfigSchema),
        description="A list of host objects.",
    )
