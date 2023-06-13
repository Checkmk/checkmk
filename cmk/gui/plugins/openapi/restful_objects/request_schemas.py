#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from marshmallow_oneofschema import OneOfSchema

from cmk.utils.livestatus_helpers import tables
from cmk.utils.regex import GROUP_NAME_PATTERN, REGEX_ID, WATO_FOLDER_PATH_NAME_REGEX

from cmk.gui import fields as gui_fields
from cmk.gui.fields import AuxTagIDField
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.livestatus_utils.commands.acknowledgments import acknowledge_service_problem
from cmk.gui.livestatus_utils.commands.downtimes import (
    schedule_host_downtime,
    schedule_hostgroup_host_downtime,
    schedule_service_downtime,
    schedule_servicegroup_service_downtime,
)
from cmk.gui.plugins.openapi.utils import param_description
from cmk.gui.watolib.tags import tag_group_exists

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


class LinkHostUUID(BaseSchema):
    uuid = fields.UUID(
        required=True,
        example="34e4c967-1591-4883-8cdf-0e335b09618d",
        description="A valid UUID.",
    )


class RegisterHost(BaseSchema):
    uuid = fields.UUID(
        required=True,
        example="34e4c967-1591-4883-8cdf-0e335b09618d",
        description="A valid UUID.",
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
    )


class InputContactGroup(InputGroup):
    """Creating a contact group"""

    name = fields.String(
        required=True,
        example="OnCall",
        description="The name of the contact group.",
        pattern=GROUP_NAME_PATTERN,
    )
    alias = fields.String(
        required=True,
        description="The name used for displaying in the GUI.",
        example="Not on Sundays.",
    )


class BulkInputContactGroup(BaseSchema):
    """Bulk creating contact groups"""

    # TODO: add unique entries attribute
    entries = fields.List(
        fields.Nested(InputContactGroup),
        example=[
            {
                "name": "OnCall",
                "alias": "Not on Sundays",
            }
        ],
        uniqueItems=True,
        description="A collection of contact group entries.",
    )


class UpdateContactGroup(BaseSchema):
    """Updating a contact group"""

    name = gui_fields.GroupField(
        group_type="contact",
        description="The name of the contact group.",
        example="OnCall",
        required=True,
        should_exist=True,
    )
    attributes = fields.Nested(UpdateGroup)


class BulkUpdateContactGroup(BaseSchema):
    """Bulk update contact groups"""

    entries = fields.List(
        fields.Nested(UpdateContactGroup),
        example=[
            {
                "name": "OnCall",
                "attributes": {
                    "alias": "Not on Sundays",
                },
            }
        ],
        description="A list of contact group entries.",
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
    )


class MoveFolder(BaseSchema):
    destination = gui_fields.FolderField(
        required=True,
        description="Where the folder has to be moved to.",
        example="~my~fine/folder",
    )


class CreateDowntimeBase(BaseSchema):
    start_time = fields.DateTime(
        format="iso8601",
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The start datetime of the new downtime. The format has to conform to the ISO 8601 profile",
    )
    end_time = fields.DateTime(
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The end datetime of the new downtime. The format has to conform to the ISO 8601 profile",
        format="iso8601",
    )
    recur = fields.String(
        required=False,
        enum=[
            "fixed",
            "hour",
            "day",
            "week",
            "second_week",
            "fourth_week",
            "weekday_start",
            "weekday_end",
            "day_of_month",
        ],
        description=param_description(schedule_host_downtime.__doc__, "recur"),
        example="hour",
        load_default="fixed",
    )
    duration = fields.Integer(
        required=False,
        description=param_description(schedule_host_downtime.__doc__, "duration"),
        example=60,
        load_default=0,
    )
    comment = fields.String(required=False, example="Security updates")


class CreateHostDowntimeBase(CreateDowntimeBase):
    downtime_type = fields.String(
        required=True,
        description="The type of downtime to create.",
        enum=["host", "hostgroup", "host_by_query"],
        example="host",
    )


class CreateServiceDowntimeBase(CreateDowntimeBase):
    downtime_type = fields.String(
        required=True,
        description="The type of downtime to create.",
        enum=["service", "servicegroup", "service_by_query"],
        example="service",
    )


SERVICE_DESCRIPTION_FIELD = fields.String(required=False, example="CPU utilization")

HOST_DURATION = fields.Integer(
    required=False,
    description=param_description(schedule_host_downtime.__doc__, "duration"),
    example=60,
    load_default=0,
)

SERVICE_DURATION = fields.Integer(
    required=False,
    description=param_description(schedule_service_downtime.__doc__, "duration"),
    example=60,
    load_default=0,
)

INCLUDE_ALL_SERVICES = fields.Boolean(
    description="If set, downtimes for all services associated with the given host will be scheduled.",
    required=False,
    load_default=False,
    example=True,
)


class CreateHostDowntime(CreateHostDowntimeBase):
    host_name = MONITORED_HOST
    duration = HOST_DURATION


class CreateServiceDowntime(CreateServiceDowntimeBase):
    # We rely on the code in the endpoint itself to check if the host is there or not.
    # Here, we don't want to 403 when the host is inaccessible to the user,
    # but the specific service on that host can be accessed.
    host_name = gui_fields.HostField(should_exist=None)
    service_descriptions = fields.List(
        fields.String(),
        uniqueItems=True,
        required=True,
        example=["CPU utilization", "Memory"],
        description=param_description(schedule_service_downtime.__doc__, "service_description"),
    )
    duration = fields.Integer(
        required=False,
        description=param_description(schedule_service_downtime.__doc__, "duration"),
        example=60,
        load_default=0,
    )


class CreateServiceGroupDowntime(CreateServiceDowntimeBase):
    servicegroup_name = gui_fields.GroupField(
        group_type="service",
        example="windows",
        required=True,
        description=param_description(
            schedule_servicegroup_service_downtime.__doc__, "servicegroup_name"
        ),
    )
    duration = HOST_DURATION


class CreateHostGroupDowntime(CreateHostDowntimeBase):
    hostgroup_name = gui_fields.GroupField(
        group_type="host",
        example="windows",
        required=True,
        description=param_description(schedule_hostgroup_host_downtime.__doc__, "hostgroup_name"),
        should_exist=True,
    )
    duration = HOST_DURATION


class CreateHostQueryDowntime(CreateHostDowntimeBase):
    query = gui_fields.query_field(tables.Hosts, required=True)
    duration = HOST_DURATION


class CreateServiceQueryDowntime(CreateServiceDowntimeBase):
    query = gui_fields.query_field(tables.Services, required=True)
    duration = SERVICE_DURATION


class CreateHostRelatedDowntime(OneOfSchema):
    type_field = "downtime_type"
    type_field_remove = False
    type_schemas = {
        "host": CreateHostDowntime,
        "hostgroup": CreateHostGroupDowntime,
        "host_by_query": CreateHostQueryDowntime,
    }


class CreateServiceRelatedDowntime(OneOfSchema):
    type_field = "downtime_type"
    type_field_remove = False
    type_schemas = {
        "service": CreateServiceDowntime,
        "servicegroup": CreateServiceGroupDowntime,
        "service_by_query": CreateServiceQueryDowntime,
    }


class DeleteDowntimeBase(BaseSchema):
    delete_type = fields.String(
        required=True,
        description="The option how to delete a downtime.",
        enum=["params", "query", "by_id"],
        example="params",
    )


class DeleteDowntimeById(DeleteDowntimeBase):
    downtime_id = fields.String(
        description="The id of the downtime",
        example="54",
        required=True,
    )


class DeleteDowntimeByName(DeleteDowntimeBase):
    host_name = gui_fields.HostField(
        required=True,
        should_exist=None,  # we don't care
        description="If set alone, then all downtimes of the host will be removed.",
        example="example.com",
    )
    service_descriptions = fields.List(
        SERVICE_DESCRIPTION_FIELD,
        description="If set, the downtimes of the listed services of the specified host will be "
        "removed. If a service has multiple downtimes then all will be removed",
        required=False,
        example=["CPU load", "Memory"],
    )


class DeleteDowntimeByQuery(DeleteDowntimeBase):
    query = gui_fields.query_field(tables.Downtimes, required=True)


class DeleteDowntime(OneOfSchema):
    type_field = "delete_type"
    type_field_remove = False
    type_schemas = {
        "by_id": DeleteDowntimeById,
        "params": DeleteDowntimeByName,
        "query": DeleteDowntimeByQuery,
    }


AUTH_ENFORCE_PASSWORD_CHANGE = fields.Boolean(
    required=False,
    description="If set to True, the user will be forced to change his password on the next "
    "login or access. Defaults to False",
    example=False,
    load_default=False,
)


class HostTagGroupId(fields.String):
    """A field representing a host tag group id"""

    default_error_messages = {
        "invalid": "The specified tag group id is already in use: {name!r}",
    }

    def _validate(self, value):
        super()._validate(value)
        group_exists = tag_group_exists(value, builtin_included=True)
        if group_exists:
            raise self.make_error("invalid", name=value)


class Tags(fields.List):
    """A field representing a tags list"""

    default_error_messages = {
        "duplicate": "Tags IDs must be unique. You've used the following at least twice: {name!r}",
        "invalid_none": "Cannot use an empty tag ID for single entry",
        "multi_none": "Only one tag id is allowed to be empty",
    }

    def __init__(
        self,
        cls,
        example,
        required=True,
        validate=None,
        **kwargs,
    ):
        super().__init__(
            cls_or_instance=cls,
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        self._unique_ids(value)
        self._valid_none_tag(value)

    def _valid_none_tag(self, value):
        none_tag_exists = False
        for tag in value:
            tag_id = tag.get("id")
            if tag_id is None:
                if len(value) == 1:
                    raise self.make_error("invalid_none")

                if none_tag_exists:
                    raise self.make_error("multi_none")

                none_tag_exists = True

    def _unique_ids(self, tags):
        seen_ids = set()
        for tag in tags:
            tag_id = tag.get("id")
            if tag_id in seen_ids:
                raise self.make_error("duplicate", name=tag_id)
            seen_ids.add(tag_id)


class HostTag(BaseSchema):
    ident = fields.String(
        required=False,
        example="tag_id",
        description="An unique id for the tag",
        load_default=None,
        attribute="id",
    )
    title = fields.String(
        required=True,
        example="Tag",
        description="The title of the tag",
    )
    aux_tags = fields.List(
        AuxTagIDField(
            required=False,
            presence="should_exist",
        ),
        description="The list of auxiliary tag ids. Built-in tags (ip-v4, ip-v6, snmp, tcp, ping) and custom defined tags are allowed.",
        example=["ip-v4, ip-v6"],
        required=False,
        load_default=list,
    )


class InputHostTagGroup(BaseSchema):
    ident = HostTagGroupId(
        required=True,
        example="group_id",
        description="An id for the host tag group",
        attribute="id",
        pattern=REGEX_ID,
    )
    title = fields.String(
        required=True,
        example="Kubernetes",
        description="A title for the host tag",
    )
    topic = fields.String(
        example="Data Sources",
        description="Different tags can be grouped in a topic",
    )

    help = fields.String(
        required=False,
        example="Kubernetes Pods",
        description="A help description for the tag group",
        load_default="",
    )
    tags = Tags(
        fields.Nested(HostTag),
        required=True,
        example=[{"ident": "pod", "title": "Pod"}],
        description="A list of host tags belonging to the host tag group",
        minLength=1,
    )


class DeleteHostTagGroup(BaseSchema):
    repair = fields.Boolean(
        required=False,
        load_default=False,
        example=False,
        description="The host tag group can still be in use. Setting repair to True gives permission to automatically remove the tag from the affected hosts.",
    )


class UpdateHostTagGroup(BaseSchema):
    title = fields.String(
        required=False,
        example="Kubernetes",
        description="A title for the host tag",
    )
    topic = fields.String(
        required=False,
        example="Data Sources",
        description="Different tags can be grouped in a topic",
    )

    help = fields.String(
        required=False,
        example="Kubernetes Pods",
        description="A help description for the tag group",
    )
    tags = Tags(
        fields.Nested(HostTag),
        required=False,
        example=[{"ident": "pod", "title": "Pod"}],
        description="A list of host tags belonging to the host tag group",
        minLength=1,
    )
    repair = fields.Boolean(
        required=False,
        load_default=False,
        example=False,
        description="The host tag group can be in use by other hosts. Setting repair to True gives permission to automatically update the tag from the affected hosts.",
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


class BulkDeleteDowntime(BaseSchema):
    host_name = MONITORED_HOST
    entries = fields.List(
        fields.Integer(
            required=True,
            description="The id for either a host downtime or service downtime",
            example=1120,
        ),
        required=True,
        example=[1120, 1121],
        description="A list of downtime ids.",
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


class BulkDeleteContactGroup(BaseSchema):
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the contact group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
        description="A list of contract group names.",
    )
