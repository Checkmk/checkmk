#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema

from cmk import fields

EXISTING_FOLDER = gui_fields.FolderField(
    example="/",
    required=True,
)

EXISTING_HOST_NAME = gui_fields.HostField(
    description="The hostname or IP address itself.",
    required=True,
    should_exist=True,
)


class CreateClusterHost(BaseSchema):
    host_name = gui_fields.HostField(
        description="The hostname of the cluster host.",
        required=True,
        should_exist=False,
    )
    folder = EXISTING_FOLDER
    attributes = gui_fields.host_attributes_field(
        "cluster",
        "create",
        "inbound",
        description="Attributes to set on the newly created host.",
        example={"ipaddress": "192.168.0.123"},
    )
    nodes = fields.List(
        EXISTING_HOST_NAME,
        description="Nodes where the newly created host should be the cluster-container of.",
        required=True,
        example=["host1", "host2", "host3"],
    )


class UpdateNodes(BaseSchema):
    nodes = fields.List(
        gui_fields.HostField(should_be_cluster=False),
        description="Nodes where the newly created host should be the cluster-container of.",
        required=True,
        example=["host1", "host2", "host3"],
    )


class CreateHost(BaseSchema):
    host_name = gui_fields.HostField(
        description="The hostname or IP address of the host to be created.",
        required=True,
        should_exist=False,
    )
    folder = EXISTING_FOLDER
    attributes = gui_fields.host_attributes_field(
        "host",
        "create",
        "inbound",
        description="Attributes to set on the newly created host.",
        example={"ipaddress": "192.168.0.123"},
    )


class BulkCreateHost(BaseSchema):
    entries = fields.List(
        fields.Nested(CreateHost),
        example=[
            {
                "host_name": "example.com",
                "folder": "/",
                "attributes": {},
            }
        ],
        uniqueItems=True,
        description="A list of host entries.",
        required=True,
    )


class UpdateHost(BaseSchema):
    """Updating of a host

    Only the `attributes` and `nodes` values may be changed.

    Required attributes:

      * none

    Optional arguments:

      * `attributes`
      * `update_attributes`
      * `remove_attributes`
    """

    attributes = gui_fields.host_attributes_field(
        "host",
        "update",
        "inbound",
        description=(
            "Replace all currently set attributes on the host, with these attributes. "
            "Any previously set attributes which are not given here will be removed."
        ),
        example={"ipaddress": "192.168.0.123"},
        required=False,
    )
    update_attributes = gui_fields.host_attributes_field(
        "host",
        "update",
        "inbound",
        description=(
            "Just update the hosts attributes with these attributes. The previously set "
            "attributes will be overwritten."
        ),
        example={"ipaddress": "192.168.0.123"},
        required=False,
    )
    remove_attributes = fields.List(
        fields.String(),
        description="A list of attributes which should be removed.",
        example=["tag_foobar"],
        required=False,
        load_default=list,
    )


class UpdateHostEntry(UpdateHost):
    host_name = gui_fields.HostField(
        description="The hostname or IP address itself.",
        required=True,
        should_exist=True,
    )


class BulkUpdateHost(BaseSchema):
    entries = fields.List(
        fields.Nested(UpdateHostEntry),
        example=[{"host_name": "example.com", "attributes": {}}],
        description="A list of host entries.",
        required=True,
    )


class RenameHost(BaseSchema):
    new_name = gui_fields.HostField(
        description="The new name of the existing host.",
        required=True,
        should_exist=False,
        example="newhost",
    )


class MoveHost(BaseSchema):
    target_folder = gui_fields.FolderField(
        required=True,
        description="The path of the target folder where the host is supposed to be moved to.",
        example="~my~fine~folder",
    )


class BulkDeleteHost(BaseSchema):
    entries = fields.List(
        EXISTING_HOST_NAME,
        required=True,
        example=["example", "sample"],
        description="A list of host names.",
    )
