#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.regex import GROUP_NAME_PATTERN, WATO_FOLDER_PATH_NAME_REGEX

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.livestatus_utils.commands.acknowledgments import acknowledge_service_problem
from cmk.gui.livestatus_utils.commands.downtimes import schedule_servicegroup_service_downtime
from cmk.gui.plugins.openapi.utils import param_description

from cmk import fields

EXISTING_HOST_NAME = gui_fields.HostField(
    description="The hostname or IP address itself.",
    required=True,
    should_exist=True,
)

MONITORED_HOST = gui_fields.HostField(
    description="The hostname or IP address itself.",
    example="example.com",
    should_exist=None,
    should_be_monitored=True,
    required=True,
)

EXISTING_FOLDER = gui_fields.FolderField(
    example="/",
    required=True,
)

SERVICEGROUP_NAME = fields.String(
    required=True,
    description=param_description(
        schedule_servicegroup_service_downtime.__doc__, "servicegroup_name"
    ),
    example="Webservers",
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


EXISTING_HOST_GROUP_NAME = gui_fields.GroupField(
    group_type="host",
    example="windows",
    required=True,
    description="The name of the host group.",
    should_exist=True,
)

EXISTING_SERVICE_GROUP_NAME = gui_fields.GroupField(
    group_type="service",
    example="windows",
    required=True,
    description="The name of the service group.",
    should_exist=True,
)


class InputGroup(BaseSchema):
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
        allow_global=True,
    )


class InputHostGroup(InputGroup):
    """Creating a host group"""

    name = gui_fields.GroupField(
        group_type="host",
        example="windows",
        required=True,
        should_exist=False,
        description="A name used as identifier",
        pattern=GROUP_NAME_PATTERN,
    )
    alias = fields.String(
        required=True,
        description="The name used for displaying in the GUI.",
        example="Windows Servers",
    )


class BulkInputHostGroup(BaseSchema):
    """Bulk creating host groups"""

    entries = fields.List(
        fields.Nested(InputHostGroup),
        example=[
            {
                "name": "windows",
                "alias": "Windows Servers",
            }
        ],
        uniqueItems=True,
        description="A list of host group entries.",
        required=True,
    )


class UpdateGroup(BaseSchema):
    alias = fields.String(
        example="Example Group",
        description="The name used for displaying in the GUI.",
        required=True,
    )
    customer = gui_fields.customer_field(
        required=False,
        should_exist=True,
        allow_global=True,
    )


class UpdateHostGroup(BaseSchema):
    """Updating a host group"""

    name = EXISTING_HOST_GROUP_NAME
    attributes = fields.Nested(UpdateGroup)


class BulkUpdateHostGroup(BaseSchema):
    """Bulk update host groups"""

    entries = fields.List(
        fields.Nested(UpdateHostGroup),
        example=[
            {
                "name": "windows",
                "attributes": {
                    "alias": "Windows Servers",
                },
            }
        ],
        description="A list of host group entries.",
        required=True,
    )


class InputServiceGroup(InputGroup):
    """Creating a service group"""

    name = gui_fields.GroupField(
        group_type="service",
        example="windows",
        required=True,
        description="A name used as identifier",
        should_exist=False,
        pattern=GROUP_NAME_PATTERN,
    )
    alias = fields.String(
        description="The name used for displaying in the GUI.",
        example="Environment Sensors",
        required=True,
    )


class BulkInputServiceGroup(BaseSchema):
    """Bulk creating service groups"""

    entries = fields.List(
        fields.Nested(InputServiceGroup),
        example=[
            {
                "name": "environment",
                "alias": "Environment Sensors",
            }
        ],
        uniqueItems=True,
        description="A list of service group entries.",
        required=True,
    )


class UpdateServiceGroup(BaseSchema):
    """Updating a service group"""

    name = EXISTING_SERVICE_GROUP_NAME
    attributes = fields.Nested(UpdateGroup)


class BulkUpdateServiceGroup(BaseSchema):
    """Bulk update service groups"""

    entries = fields.List(
        fields.Nested(UpdateServiceGroup),
        example=[
            {
                "name": "windows",
                "attributes": {
                    "alias": "Windows Servers",
                },
            }
        ],
        description="A list of service group entries.",
        required=True,
    )


class CreateFolder(BaseSchema):
    """Creating a folder

    Every folder needs a parent folder to reside in. The uppermost folder is called the "root"
    Folder and has the fixed identifier "root".

    Parameters:

     * `name` is the actual folder-name on disk. This will be autogenerated from the title, if not given.
     * `title` is meant for humans to read.
     * `parent` is the identifier for the parent-folder. This identifier stays the same,
        even if the parent folder is being moved.
     * `attributes` can hold special configuration parameters which control various aspects of
        the monitoring system. Most of these attributes will be inherited by hosts within that
        folder. For more information please have a look at the
        [Host Administration chapter of the user guide](https://docs.checkmk.com/master/en/wato_hosts.html#intro).
    """

    name = fields.String(
        description=(
            "The filesystem directory name (not path!) of the folder. No slashes are allowed."
        ),
        pattern=WATO_FOLDER_PATH_NAME_REGEX,
        example="production",
        minLength=1,
    )
    title = fields.String(
        required=True,
        description="The folder title as displayed in the user interface.",
        example="Production Hosts",
    )
    parent = gui_fields.FolderField(
        required=True,
        description=(
            "The folder in which the new folder shall be placed in. The root-folder is "
            "specified by '/'."
        ),
        example="/",
    )
    attributes = gui_fields.host_attributes_field(
        "folder",
        "create",
        "inbound",
        required=False,
        description=(
            "Specific attributes to apply for all hosts in this folder " "(among other things)."
        ),
        example={"tag_criticality": "prod"},
    )


class BulkCreateFolder(BaseSchema):
    entries = fields.List(
        fields.Nested(CreateFolder),
        example=[
            {
                "name": "production",
                "parent": "root",
                "attributes": {"foo": "bar"},
            }
        ],
        uniqueItems=True,
    )


class UpdateFolder(BaseSchema):
    """Updating a folder"""

    title = fields.String(
        example="Virtual Servers.",
        required=False,
        description="The title of the folder. Used in the GUI.",
    )
    attributes = gui_fields.host_attributes_field(
        "folder",
        "update",
        "inbound",
        description=(
            "Replace all attributes with the ones given in this field. Already set"
            "attributes, not given here, will be removed."
        ),
        example={"tag_networking": "wan"},
        required=False,
    )
    update_attributes = gui_fields.host_attributes_field(
        "folder",
        "update",
        "inbound",
        description=(
            "Only set the attributes which are given in this field. Already set "
            "attributes will not be touched."
        ),
        example={"tag_criticality": "prod"},
        required=False,
    )
    remove_attributes = fields.List(
        fields.String(),
        description="A list of attributes which should be removed.",
        example=["tag_foobar"],
        required=False,
        load_default=list,
    )


class UpdateFolderEntry(UpdateFolder):
    folder = EXISTING_FOLDER


class BulkUpdateFolder(BaseSchema):
    entries = fields.Nested(
        UpdateFolderEntry,
        many=True,
        example=[
            {
                "remove_attributes": ["tag_foobar"],
            }
        ],
        description="A list of folder entries.",
        required=True,
    )


class MoveFolder(BaseSchema):
    destination = gui_fields.FolderField(
        required=True,
        description="Where the folder has to be moved to.",
        example="~my~fine/folder",
    )


SERVICE_DESCRIPTION_FIELD = fields.String(required=False, example="CPU utilization")

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


class BulkDeleteHost(BaseSchema):
    entries = fields.List(
        EXISTING_HOST_NAME,
        required=True,
        example=["example", "sample"],
        description="A list of host names.",
    )


class BulkDeleteFolder(BaseSchema):
    entries = fields.List(
        EXISTING_FOLDER,
        required=True,
        example=["production", "secondproduction"],
    )


class BulkDeleteHostGroup(BaseSchema):
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the host group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
        description="A list of host group names.",
    )


class BulkDeleteServiceGroup(BaseSchema):
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the service group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
        description="A list of service group names.",
    )
