#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import MutableMapping
from typing import Any, Literal

import marshmallow
from marshmallow_oneofschema import OneOfSchema

from cmk.utils.livestatus_helpers import tables
from cmk.utils.regex import GROUP_NAME_PATTERN, REGEX_ID, WATO_FOLDER_PATH_NAME_REGEX
from cmk.utils.type_defs import UserId

from cmk.gui import fields as gui_fields
from cmk.gui.config import builtin_role_ids
from cmk.gui.exceptions import MKInternalError
from cmk.gui.fields import AuxTagIDField
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.livestatus_utils.commands.acknowledgments import (
    acknowledge_host_problem,
    acknowledge_hostgroup_problem,
    acknowledge_service_problem,
)
from cmk.gui.livestatus_utils.commands.downtimes import (
    schedule_host_downtime,
    schedule_hostgroup_host_downtime,
    schedule_service_downtime,
    schedule_servicegroup_service_downtime,
)
from cmk.gui.permissions import permission_registry
from cmk.gui.plugins.openapi.utils import param_description
from cmk.gui.plugins.userdb.utils import user_attribute_registry
from cmk.gui.userdb import load_users, register_custom_user_attributes
from cmk.gui.watolib import userroles
from cmk.gui.watolib.custom_attributes import load_custom_attrs_from_mk_file
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
        required=True,
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

     * `name` is the actual folder-name on disk.
     * `title` is meant for humans to read.
     * `parent` is the identifier for the parent-folder. This identifier stays the same,
        even if the parent folder is being moved.
     * `attributes` can hold special configuration parameters which control various aspects of
        the monitoring system. Most of these attributes will be inherited by hosts within that
        folder. For more information please have a look at the
        [Host Administration chapter of the user guide](https://docs.checkmk.com/master/en/wato_hosts.html#Introduction).
    """

    name = fields.String(
        description=(
            "The filesystem directory name (not path!) of the folder." " No slashes are allowed."
        ),
        required=True,
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
        example=3600,
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
    example=3600,
    load_default=0,
)

SERVICE_DURATION = fields.Integer(
    required=False,
    description=param_description(schedule_service_downtime.__doc__, "duration"),
    example=3600,
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
    host_name = EXISTING_HOST_NAME  # Note: You don't need access to the host, only to the service
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
        example=3600,
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


class InputPassword(BaseSchema):
    ident = gui_fields.PasswordIdent(
        example="pass",
        description="An unique identifier for the password",
        should_exist=False,
        pattern=REGEX_ID,
    )
    title = fields.String(
        required=True,
        example="Kubernetes login",
        description="A title for the password",
    )
    comment = fields.String(
        required=False,
        example="Kommentar",
        description="A comment for the password",
        load_default="",
    )

    documentation_url = fields.String(
        required=False,
        attribute="docu_url",
        example="localhost",
        description="An optional URL pointing to documentation or any other page. You can use either global URLs (beginning with http://), absolute local urls (beginning with /) or relative URLs (that are relative to check_mk/).",
        load_default="",
    )

    password = fields.String(
        required=True,
        example="password",
        description="The password string",
    )

    owner = gui_fields.PasswordOwner(
        example="admin",
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        required=True,
        attribute="owned_by",
    )

    shared = fields.List(
        gui_fields.PasswordShare(
            example="all",
            description="By default only the members of the owner contact group are permitted to use a a configured password. It is possible to share a password with other groups of users to make them able to use a password in checks.",
        ),
        example=["all"],
        description="The list of members to share the password with",
        required=False,
        attribute="shared_with",
        load_default=list,
    )
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
        allow_global=True,
    )


class UpdatePassword(BaseSchema):
    title = fields.String(
        required=False,
        example="Kubernetes login",
        description="A title for the password",
    )

    comment = fields.String(
        required=False,
        example="Kommentar",
        description="A comment for the password",
    )

    documentation_url = fields.String(
        required=False,
        attribute="docu_url",
        example="localhost",
        description="An optional URL pointing to documentation or any other page. You can use either global URLs (beginning with http://), absolute local urls (beginning with /) or relative URLs (that are relative to check_mk/).",
    )

    password = fields.String(
        required=False,
        example="password",
        description="The password string",
    )

    owner = gui_fields.PasswordOwner(
        example="admin",
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        required=False,
        attribute="owned_by",
    )

    shared = fields.List(
        gui_fields.PasswordShare(
            example="all",
            description="By default only the members of the owner contact group are permitted to use a a configured password. "
            "It is possible to share a password with other groups of users to make them able to use a password in checks.",
        ),
        example=["all"],
        description="The list of members to share the password with",
        required=False,
        attribute="shared_with",
    )
    customer = gui_fields.customer_field(
        required=False,
        should_exist=True,
        allow_global=True,
    )


class Username(fields.String):
    default_error_messages = {
        "should_exist": "Username missing: {username!r}",
        "should_not_exist": "Username {username!r} already exists",
        "invalid_name": "Username {username!r} is not a valid checkmk username",
    }

    def __init__(  # type: ignore[no-untyped-def]
        self,
        example,
        required=True,
        validate=None,
        should_exist: bool = True,
        **kwargs,
    ):
        self._should_exist = should_exist
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        try:
            UserId(value)
        except ValueError:
            raise self.make_error("invalid_name", username=value)

        # TODO: change to names list only
        usernames = load_users()
        if self._should_exist and value not in usernames:
            raise self.make_error("should_exist", username=value)
        if not self._should_exist and value in usernames:
            raise self.make_error("should_not_exist", username=value)


class UserRoleID(fields.String):
    default_error_messages = {
        "should_not_exist": "The role should not exist but it does: {role!r}",
        "should_exist": "The role should exist but it doesn't: {role!r}",
        "should_be_custom": "The role should be a custom role but it's not: {role!r}",
        "should_be_builtin": "The role should be a builtin role but it's not: {role!r}",
    }

    def __init__(  # type: ignore[no-untyped-def]
        self,
        presence: Literal["should_exist", "should_not_exist", "ignore"] = "ignore",
        userrole_type: Literal["should_be_custom", "should_be_builtin", "ignore"] = "ignore",
        required=False,
        **kwargs,
    ) -> None:
        super().__init__(required=required, **kwargs)
        self.presence = presence
        self.userrole_type = userrole_type

    def _validate(self, value) -> None:  # type: ignore[no-untyped-def]
        super()._validate(value)

        if self.presence == "should_not_exist":
            if userroles.role_exists(value):
                raise self.make_error("should_not_exist", role=value)

        elif self.presence == "should_exist":
            if not userroles.role_exists(value):
                raise self.make_error("should_exist", role=value)

        if self.userrole_type == "should_be_builtin":
            if value not in builtin_role_ids:
                raise self.make_error("should_be_builtin", role=value)

        elif self.userrole_type == "should_be_custom":
            if value in builtin_role_ids:
                raise self.make_error("should_be_custom", role=value)


class CustomTimeRange(BaseSchema):
    # TODO: gui_fields.Dict validation also for Timperiods
    start_time = fields.DateTime(
        format="iso8601",
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The start datetime of the time period. The format has to conform to the ISO 8601 profile",
    )
    end_time = fields.DateTime(
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The end datetime of the time period. The format has to conform to the ISO 8601 profile",
        format="iso8601",
    )


class DisabledNotifications(BaseSchema):
    disable = fields.Boolean(
        required=False,
        description="Option if all notifications should be temporarily disabled",
        example=False,
    )
    timerange = fields.Nested(
        CustomTimeRange,
        description="A custom timerange during which notifications are disabled",
        required=False,
        example={
            "start_time": "2017-07-21T17:32:28Z",
            "end_time": "2017-07-21T18:32:28Z",
        },
    )


class UserInterfaceAttributes(BaseSchema):
    interface_theme = fields.String(
        required=False,
        description="The theme of the interface",
        enum=["default", "dark", "light"],
        load_default="default",
    )
    sidebar_position = fields.String(
        required=False,
        description="The position of the sidebar",
        enum=["left", "right"],
        load_default="right",
    )
    navigation_bar_icons = fields.String(
        required=False,
        description="This option decides if icons in the navigation bar should show/hide the "
        "respective titles",
        enum=["hide", "show"],
        load_default="hide",
    )
    mega_menu_icons = fields.String(
        required=False,
        description="This option decides if colored icon should be shown foe every entry in the "
        "mega menus or alternatively only for the headlines (the 'topics')",
        enum=["topic", "entry"],
        load_default="topic",
    )
    show_mode = fields.String(
        required=False,
        description="This option decides what show mode should be used for unvisited menus."
        " Alternatively, this option can also be used to enforce show more removing the three dots "
        "for all menus.",
        enum=["default", "default_show_less", "default_show_more", "enforce_show_more"],
        load_default="default",
    )


class UserInterfaceUpdateAttributes(BaseSchema):
    interface_theme = fields.String(
        required=False,
        description="The theme of the interface",
        enum=["default", "dark", "light"],
    )
    sidebar_position = fields.String(
        required=False,
        description="The position of the sidebar",
        enum=["left", "right"],
    )
    navigation_bar_icons = fields.String(
        required=False,
        description="This option decides if icons in the navigation bar should show/hide the "
        "respective titles",
        enum=["hide", "show"],
    )
    mega_menu_icons = fields.String(
        required=False,
        description="This option decides if colored icon should be shown foe every entry in the "
        "mega menus or alternatively only for the headlines (the 'topics')",
        enum=["topic", "entry"],
    )
    show_mode = fields.String(
        required=False,
        description="This option decides what show mode should be used for unvisited menus."
        " Alternatively, this option can also be used to enforce show more removing the three dots "
        "for all menus.",
        enum=["default", "default_show_less", "default_show_more", "enforce_show_more"],
    )


AUTH_PASSWORD = fields.String(
    required=False,
    description="The password for login",
    example="password",
    minLength=1,
)

AUTH_SECRET = fields.String(
    required=False,
    description="For accounts used by automation processes (such as fetching data from views "
    "for further procession). This is the automation secret",
    example="DEYQEQQPYCFFBYH@AVMC",
)

AUTH_ENFORCE_PASSWORD_CHANGE = fields.Boolean(
    required=False,
    description="If set to True, the user will be forced to change his password on the next "
    "login or access. Defaults to False",
    example=False,
    load_default=False,
)

AUTH_CREATE_TYPE = fields.String(
    required=False,
    description="The authentication type",
    enum=["automation", "password"],
    example="password",
)

AUTH_UPDATE_TYPE = fields.String(
    required=True,
    description="The authentication type",
    enum=["automation", "password", "remove"],
    example="password",
)


class AuthSecret(BaseSchema):
    auth_type = AUTH_CREATE_TYPE
    secret = AUTH_SECRET


class AuthPassword(BaseSchema):
    auth_type = AUTH_CREATE_TYPE
    password = AUTH_PASSWORD
    enforce_password_change = fields.Boolean(
        required=False,
        description="If set to True, the user will be forced to change his password on the next "
        "login or access. Defaults to False",
        example=False,
        load_default=False,
    )


class AuthUpdateSecret(BaseSchema):
    auth_type = AUTH_UPDATE_TYPE
    secret = AUTH_SECRET


class AuthUpdatePassword(BaseSchema):
    auth_type = AUTH_UPDATE_TYPE
    password = AUTH_PASSWORD
    enforce_password_change = fields.Boolean(
        required=False,
        description="If set to True, the user will be forced to change his password on the next "
        "login or access",
        example=False,
    )


class AuthUpdateRemove(BaseSchema):
    auth_type = AUTH_UPDATE_TYPE


class AuthOption(OneOfSchema):
    type_field = "auth_type"
    type_field_remove = False
    type_schemas = {
        "password": AuthPassword,
        "automation": AuthSecret,
    }


class AuthUpdateOption(OneOfSchema):
    type_field = "auth_type"
    type_field_remove = False
    type_schemas = {
        "password": AuthUpdatePassword,
        "automation": AuthUpdateSecret,
        "remove": AuthUpdateRemove,
    }


class IdleOption(BaseSchema):
    option = fields.String(
        required=True,
        description="Specify if the idle timeout should use the global configuration, be disabled "
        "or use an individual duration",
        enum=["global", "disable", "individual"],
        example=False,
    )
    duration = fields.Integer(
        required=False,
        description="The duration in seconds of the individual idle timeout if individual is "
        "selected as idle timeout option.",
        example=3600,
        load_default=3600,
    )


class UserContactOption(BaseSchema):
    email = fields.String(
        required=True,
        description="The mail address of the user. Required if the user is a monitoring"
        "contact and receives notifications via mail.",
        example="user@example.com",
    )
    # User cannot enable fallback contact if no email is specified
    fallback_contact = fields.Boolean(
        description="In case none of your notification rules handles a certain event a notification "
        "will be sent to the specified email",
        required=False,
        load_default=False,
        example=False,
    )


class UserContactUpdateOption(BaseSchema):
    email = fields.String(
        required=False,
        description="The mail address of the user. Required if the user is a monitoring"
        "contact and receives notifications via mail.",
        example="user@example.com",
    )
    fallback_contact = fields.Boolean(
        description="In case none of your notification rules handles a certain event a notification "
        "will be sent to the specified email",
        required=False,
        example=False,
    )


class CreateUser(BaseSchema):
    class Meta:
        ordered = True
        unknown = marshmallow.INCLUDE

    username = Username(
        required=True,
        should_exist=False,
        description="An unique username for the user",
        example="cmkuser",
    )
    fullname = fields.String(
        required=True,
        description="The alias or full name of the user",
        example="Mathias Kettner",
        attribute="alias",
    )
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
        allow_global=True,
        description="By specifying a customer, you configure on which sites the user object will be available. "
        "'global' will make the object available on all sites.",
    )
    auth_option = fields.Nested(
        AuthOption,
        required=False,
        description="Authentication option for the user",
        example={"auth_type": "password", "password": "password"},
        load_default=dict,
    )
    disable_login = fields.Boolean(
        required=False,
        load_default=False,
        description="The user can be blocked from login but will remain part of the site. "
        "The disabling does not affect notification and alerts.",
        example=False,
        attribute="locked",
    )
    contact_options = fields.Nested(
        UserContactOption,
        required=False,
        description="Contact settings for the user",
        load_default=lambda: {"email": "", "fallback_contact": False},
        example={"email": "user@example.com"},
    )
    pager_address = fields.String(
        required=False,
        description="",
        example="",
        load_default="",
        attribute="pager",
    )
    idle_timeout = fields.Nested(
        IdleOption,
        required=False,
        description="Idle timeout for the user. Per default, the global configuration is used.",
        example={"option": "global"},
    )
    roles = fields.List(
        UserRoleID(
            description="An existing user role",
            required=True,
            example="user",
            presence="should_exist",
        ),
        required=False,
        load_default=list,
        description="The list of assigned roles to the user",
        example=["user"],
    )
    authorized_sites = fields.List(
        gui_fields.SiteField(allow_all_value=True),
        description="The names of the sites the user is authorized to handle.",
        example=["heute"],
        required=False,
        load_default=["all"],
    )
    contactgroups = fields.List(
        fields.String(
            description="Assign the user to one or multiple contact groups",
            required=True,
            example="all",
        ),
        required=False,
        load_default=list,
        description="Assign the user to one or multiple contact groups. If no contact group is "
        "specified then no monitoring contact will be created for the user."
        "",
        example=["all"],
    )
    disable_notifications = fields.Nested(
        DisabledNotifications,
        required=False,
        load_default=dict,
        example={"disable": False},
        description="",
    )
    # default language is not setting a key in dict
    language = fields.String(
        required=False,
        description="Configure the language to be used by the user in the user interface. Omitting "
        "this will configure the default language.",
        example="en",
        enum=["de", "en", "ro"],
    )
    interface_options = fields.Nested(
        UserInterfaceAttributes,
        required=False,
        load_default={
            "interface_theme": "default",
            "sidebar_position": "right",
            "navigation_bar_icons": "hide",
            "mega_menu_icons": "topic",
            "show_mode": "default",
        },
        example={"interface_theme": "dark"},
        description="",
    )

    @marshmallow.post_load(pass_original=True)
    def validate_custom_attributes(
        self,
        result_data: dict[str, Any],
        original_data: MutableMapping[str, Any],
        **_unused_args: Any,
    ) -> dict[str, Any]:
        register_custom_user_attributes(load_custom_attrs_from_mk_file(lock=False)["user"])

        for field in self.fields:
            original_data.pop(field, None)

        for name, value in original_data.items():
            attribute = user_attribute_registry.get(name)
            if attribute is None:
                raise marshmallow.ValidationError(f"Unknown Attribute: {name!r}")
            if not attribute.is_custom():
                raise MKInternalError(
                    f"A non custom attribute is not in the CreateUser Schema: {name!r}"
                )
            valuespec = attribute().valuespec()
            valuespec.validate_value(value, "")
            result_data[name] = value
        return result_data


class UpdateUser(BaseSchema):
    fullname = fields.String(
        required=False,
        description="The alias or full name of the user",
        example="Mathias Kettner",
        attribute="alias",
    )
    customer = gui_fields.customer_field(
        required=False,
        should_exist=True,
    )
    auth_option = fields.Nested(
        AuthUpdateOption,
        required=False,
        description="Authentication option for the user",
        example={"auth_type": "password", "password": "password"},
        load_default=dict,
    )
    disable_login = fields.Boolean(
        required=False,
        description="The user can be blocked from login but will remain part of the site. "
        "The disabling does not affect notification and alerts.",
        example=False,
        attribute="locked",
    )
    contact_options = fields.Nested(
        UserContactOption,
        required=False,
        description="Contact settings for the user",
        example={"email": "user@example.com"},
    )
    pager_address = fields.String(
        required=False,
        description="",
        example="",
        attribute="pager",
    )
    idle_timeout = fields.Nested(
        IdleOption,
        required=False,
        description="Idle timeout for the user",
        example={},
    )
    roles = fields.List(
        UserRoleID(
            description="An existing user role",
            required=True,
            example="user",
            presence="should_exist",
        ),
        required=False,
        description="The list of assigned roles to the user",
        example=["user"],
    )
    authorized_sites = fields.List(
        gui_fields.SiteField(allow_all_value=True),
        description="The names of the sites the user is authorized to handle. Specifying 'all' "
        "will grant the user access to all sites.",
        example=["heute"],
        required=False,
    )
    contactgroups = fields.List(
        fields.String(
            description="Assign the user to one or multiple contact groups",
            required=True,
            example="all",
        ),
        required=False,
        description="Assign the user to one or multiple contact groups. If no contact group is "
        "specified then no monitoring contact will be created for the user."
        "",
        example=["all"],
    )
    disable_notifications = fields.Nested(
        DisabledNotifications,
        required=False,
        example={"disabled": False},
        description="",
    )
    # default language is not setting a key in dict
    language = fields.String(
        required=False,
        description="Configure the language to be used by the user in the user interface. Omitting "
        "this will configure the default language",
        example="en",
        enum=["de", "en", "ro"],
    )
    interface_options = fields.Nested(
        UserInterfaceUpdateAttributes,
        required=False,
        example={"interface_theme": "dark"},
        description="",
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


class AcknowledgeHostProblemBase(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="The acknowledge host selection type.",
        enum=["host", "hostgroup", "host_by_query"],
        example="host",
    )
    sticky = fields.Boolean(
        required=False,
        load_default=True,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, "sticky"),
    )

    persistent = fields.Boolean(
        required=False,
        load_default=False,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, "persistent"),
    )

    notify = fields.Boolean(
        required=False,
        load_default=True,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, "notify"),
    )

    comment = fields.String(
        required=True,
        example="This was expected.",
        description=param_description(acknowledge_host_problem.__doc__, "comment"),
    )


class AcknowledgeHostProblem(AcknowledgeHostProblemBase):
    host_name = gui_fields.HostField(
        description="The name of the host.",
        should_exist=True,
        should_be_monitored=True,
        example="example.com",
        required=True,
    )


class AcknowledgeHostGroupProblem(AcknowledgeHostProblemBase):
    hostgroup_name = gui_fields.GroupField(
        group_type="host",
        example="Servers",
        required=True,
        should_exist=True,
        should_be_monitored=True,
        description=param_description(acknowledge_hostgroup_problem.__doc__, "hostgroup_name"),
    )


class AcknowledgeHostQueryProblem(AcknowledgeHostProblemBase):
    query = gui_fields.query_field(tables.Hosts, required=True)


class AcknowledgeHostRelatedProblem(OneOfSchema):
    type_field = "acknowledge_type"
    type_field_remove = False
    type_schemas = {
        "host": AcknowledgeHostProblem,
        "hostgroup": AcknowledgeHostGroupProblem,
        "host_by_query": AcknowledgeHostQueryProblem,
    }


class AcknowledgeServiceProblemBase(BaseSchema):
    acknowledge_type = fields.String(
        required=True,
        description="The acknowledge service selection type.",
        enum=["service", "servicegroup", "service_by_query"],
        example="service",
    )

    sticky = fields.Boolean(
        required=False,
        load_default=True,
        example=False,
        description=param_description(acknowledge_service_problem.__doc__, "sticky"),
    )

    persistent = fields.Boolean(
        required=False,
        load_default=False,
        example=False,
        description=param_description(acknowledge_service_problem.__doc__, "persistent"),
    )

    notify = fields.Boolean(
        required=False,
        load_default=True,
        example=False,
        description=param_description(acknowledge_service_problem.__doc__, "notify"),
    )

    comment = fields.String(
        required=True,
        example="This was expected.",
        description=param_description(acknowledge_service_problem.__doc__, "comment"),
    )


class AcknowledgeSpecificServiceProblem(AcknowledgeServiceProblemBase):
    host_name = gui_fields.HostField(
        should_exist=True,
        should_be_monitored=True,
        required=True,
    )
    service_description = fields.String(
        description="The acknowledgement process will be applied to all matching service descriptions",
        example="CPU load",
        required=True,
    )


class AcknowledgeServiceGroupProblem(AcknowledgeServiceProblemBase):
    servicegroup_name = gui_fields.GroupField(
        group_type="service",
        example="windows",
        required=True,
        description=param_description(
            schedule_servicegroup_service_downtime.__doc__, "servicegroup_name"
        ),
    )


class AcknowledgeServiceQueryProblem(AcknowledgeServiceProblemBase):
    query = gui_fields.query_field(tables.Services, required=True)


class AcknowledgeServiceRelatedProblem(OneOfSchema):
    type_field = "acknowledge_type"
    type_field_remove = False
    type_schemas = {
        "service": AcknowledgeSpecificServiceProblem,
        "servicegroup": AcknowledgeServiceGroupProblem,
        "service_by_query": AcknowledgeServiceQueryProblem,
    }


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


class X509ReqPEMUUID(BaseSchema):
    csr = gui_fields.X509ReqPEMFieldUUID(
        required=True,
        example="-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----\n",
        description="PEM-encoded X.509 CSR. The CN must a valid version-4 UUID.",
    )


class CreateCommentBase(BaseSchema):
    comment = fields.String(
        description="The comment which will be stored for the host.",
        example="Windows",
        required=True,
    )

    persistent = fields.Boolean(
        description="If set, the comment will persist a restart.",
        example=False,
        load_default=False,
        required=False,
    )


class CreateHostCommentBase(CreateCommentBase):
    comment_type = fields.String(
        required=True,
        description="How you would like to leave a comment.",
        enum=["host", "host_by_query"],
        example="host",
    )


class CreateHostComment(CreateHostCommentBase):
    host_name = gui_fields.HostField(
        description="The host name",
        should_exist=True,
        example="example.com",
        required=True,
    )


class CreateHostQueryComment(CreateHostCommentBase):
    query = gui_fields.query_field(tables.Hosts, required=False)


class CreateHostRelatedComment(OneOfSchema):
    type_field = "comment_type"
    type_field_remove = False
    type_schemas = {
        "host": CreateHostComment,
        "host_by_query": CreateHostQueryComment,
        # TODO "host_group": CreateHostGroupComment
    }


class CreateServiceCommentBase(CreateCommentBase):
    comment_type = fields.String(
        required=True,
        description="How you would like to leave a comment.",
        enum=["service", "service_by_query"],
        example="service",
    )


class CreateServiceComment(CreateServiceCommentBase):
    host_name = gui_fields.HostField(
        description="The host name",
        should_exist=True,
        example="example.com",
        required=True,
    )
    service_description = fields.String(
        description="The service description for which the comment is for. No exception is raised when the specified service description does not exist",
        example="Memory",
        required=True,
    )


class CreateServiceQueryComment(CreateServiceCommentBase):
    query = gui_fields.query_field(tables.Services, required=True)


class CreateServiceRelatedComment(OneOfSchema):
    type_field = "comment_type"
    type_field_remove = False
    type_schemas = {
        "service": CreateServiceComment,
        "service_by_query": CreateServiceQueryComment,
        # TODO "service_group": CreateServiceGroupComment
    }


class BaseBulkDelete(BaseSchema):
    delete_type = fields.String(
        required=True,
        description="How you would like to delete comments.",
        enum=["by_id", "query", "params"],
        example="delete_by_query",
    )


class DeleteCommentById(BaseBulkDelete):
    comment_id = fields.Integer(
        required=False,
        description="An integer representing a comment ID.",
        example=21,
    )


class DeleteCommentsByQuery(BaseBulkDelete):
    query = gui_fields.query_field(tables.Comments)


class DeleteCommentsByParams(BaseBulkDelete):
    host_name = gui_fields.HostField(
        description="The host name",
        should_exist=True,
        example="example.com",
        required=True,
    )
    service_descriptions = fields.List(
        SERVICE_DESCRIPTION_FIELD,
        description="If set, the comments for the listed services of the specified host will be "
        "removed. If a service has multiple comments then all will be removed",
        required=False,
        example=["CPU load", "Memory"],
    )


class DeleteComments(OneOfSchema):
    type_field = "delete_type"
    type_field_remove = False
    type_schemas = {
        "by_id": DeleteCommentById,
        "query": DeleteCommentsByQuery,
        "params": DeleteCommentsByParams,
    }


class CreateUserRole(BaseSchema):
    role_id = UserRoleID(
        required=True,
        description="Existing userrole that you want to clone.",
        example="admin",
        presence="should_exist",
    )
    new_role_id = UserRoleID(
        required=False,
        description="The new role id for the newly created user role.",
        example="limited_permissions_user",
        presence="should_not_exist",
    )
    new_alias = fields.String(
        required=False,
        description="A new alias that you want to give to the newly created user role.",
        example="user_a",
    )


class PermissionField(fields.String):
    default_error_messages = {
        "invalid_permission": "The specified permission name doesn't exist: {value!r}",
    }

    def __init__(  # type: ignore[no-untyped-def]
        self, required=True, validate=None, **kwargs
    ) -> None:
        super().__init__(
            example="general.edit_profile",
            description="The name of a permission",
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value) -> None:  # type: ignore[no-untyped-def]
        super()._validate(value)
        if value not in permission_registry:
            raise self.make_error("invalid_permission", value=value)


class EditUserRole(BaseSchema):
    new_role_id = UserRoleID(
        required=False,
        description="New role_id for the userrole that must be unique.",
        example="new_userrole_id",
        presence="should_not_exist",
    )
    new_alias = fields.String(
        required=False,
        description="New alias for the userrole that must be unique.",
        example="new_userrole_alias",
    )
    new_basedon = UserRoleID(
        required=False,
        description="A builtin user role that you want the user role to be based on.",
        example="guest",
        presence="should_exist",
        userrole_type="should_be_builtin",
    )
    new_permissions = fields.Dict(
        keys=PermissionField(),
        values=fields.String(required=True, enum=["yes", "no", "default"]),
        required=False,
        example={"general.edit_profile": "yes", "general.message": "no"},
        description="A map of permission names to their state.  The following values can be set: "
        "'yes' - the permission is active for this role."
        "'no' - the permission is deactivated for this role, even if it was active in the role it was based on."
        "'default' - takes the activation state from the role this role was based on. ",
    )
