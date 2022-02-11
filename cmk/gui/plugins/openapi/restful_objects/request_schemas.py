#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import urllib.parse

from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.defines import weekday_ids
from cmk.utils.livestatus_helpers import tables

from cmk.gui import fields as gui_fields
from cmk.gui import watolib
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
from cmk.gui.plugins.openapi.utils import param_description
from cmk.gui.userdb import load_users
from cmk.gui.watolib.groups import is_alias_used
from cmk.gui.watolib.tags import load_aux_tags, tag_group_exists
from cmk.gui.watolib.timeperiods import verify_timeperiod_name_exists

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
    attributes = gui_fields.attributes_field(
        "cluster",
        "create",
        description="Attributes to set on the newly created host.",
        example={"ipaddress": "192.168.0.123"},
    )
    nodes = gui_fields.List(
        EXISTING_HOST_NAME,
        description="Nodes where the newly created host should be the cluster-container of.",
        required=True,
        example=["host1", "host2", "host3"],
    )


class UpdateNodes(BaseSchema):
    nodes = gui_fields.List(
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
    attributes = gui_fields.attributes_field(
        "host",
        "create",
        description="Attributes to set on the newly created host.",
        example={"ipaddress": "192.168.0.123"},
    )


class BulkCreateHost(BaseSchema):
    entries = gui_fields.List(
        gui_fields.Nested(CreateHost),
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
      * `nodes`
    """

    attributes = gui_fields.attributes_field(
        "host",
        "update",
        description=(
            "Replace all currently set attributes on the host, with these attributes. "
            "Any previously set attributes which are not given here will be removed."
        ),
        example={"ipaddress": "192.168.0.123"},
        required=False,
    )
    update_attributes = gui_fields.attributes_field(
        "host",
        "update",
        description=(
            "Just update the hosts attributes with these attributes. The previously set "
            "attributes will not be touched."
        ),
        example={"ipaddress": "192.168.0.123"},
        required=False,
    )
    remove_attributes = gui_fields.attributes_field(
        "host",
        "update",
        names_only=True,
        description="A list of attributes which should be removed.",
        example=["tag_foobar"],
        load_default=list,
        required=False,
    )


class LinkHostUUID(BaseSchema):
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
    entries = gui_fields.List(
        gui_fields.Nested(UpdateHostEntry),
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
        example=urllib.parse.quote_plus("/my/fine/folder"),
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
    )
    alias = fields.String(
        description="The name used for displaying in the GUI.",
        example="Windows Servers",
    )


class BulkInputHostGroup(BaseSchema):
    """Bulk creating host groups"""

    entries = gui_fields.List(
        gui_fields.Nested(InputHostGroup),
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
    attributes = gui_fields.Nested(UpdateGroup)


class BulkUpdateHostGroup(BaseSchema):
    """Bulk update host groups"""

    entries = gui_fields.List(
        gui_fields.Nested(UpdateHostGroup),
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
    )
    alias = fields.String(
        description="The name used for displaying in the GUI.", example="Not on Sundays."
    )


class BulkInputContactGroup(BaseSchema):
    """Bulk creating contact groups"""

    # TODO: add unique entries attribute
    entries = gui_fields.List(
        gui_fields.Nested(InputContactGroup),
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
    attributes = gui_fields.Nested(UpdateGroup)


class BulkUpdateContactGroup(BaseSchema):
    """Bulk update contact groups"""

    entries = gui_fields.List(
        gui_fields.Nested(UpdateContactGroup),
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
    )
    alias = fields.String(
        description="The name used for displaying in the GUI.", example="Environment Sensors"
    )


class BulkInputServiceGroup(BaseSchema):
    """Bulk creating service groups"""

    entries = gui_fields.List(
        gui_fields.Nested(InputServiceGroup),
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
    attributes = gui_fields.Nested(UpdateGroup)


class BulkUpdateServiceGroup(BaseSchema):
    """Bulk update service groups"""

    entries = gui_fields.List(
        gui_fields.Nested(UpdateServiceGroup),
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
        pattern="[^/]+",
        example="production",
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
    attributes = gui_fields.attributes_field(
        "folder",
        "create",
        required=False,
        description=(
            "Specific attributes to apply for all hosts in this folder " "(among other things)."
        ),
        example={"tag_criticality": "prod"},
    )


class BulkCreateFolder(BaseSchema):
    entries = gui_fields.List(
        gui_fields.Nested(CreateFolder),
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
    attributes = gui_fields.attributes_field(
        "folder",
        "update",
        description=(
            "Replace all attributes with the ones given in this field. Already set"
            "attributes, not given here, will be removed."
        ),
        example={"networking": "wan"},
        required=False,
    )
    update_attributes = gui_fields.attributes_field(
        "folder",
        "update",
        description=(
            "Only set the attributes which are given in this field. Already set "
            "attributes will not be touched."
        ),
        example={"tag_criticality": "prod"},
        required=False,
    )
    remove_attributes = gui_fields.attributes_field(
        "folder",
        "update",
        description="A list of attributes which should be removed.",
        example=["tag_foobar"],
        load_default=list,
        required=False,
        names_only=True,
    )


class UpdateFolderEntry(UpdateFolder):
    folder = EXISTING_FOLDER


class BulkUpdateFolder(BaseSchema):
    entries = gui_fields.Nested(
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
        example=urllib.parse.quote_plus("/my/fine/folder"),
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


class TimePeriodName(fields.String):
    """A field representing a time_period name"""

    default_error_messages = {
        "should_exist": "Name missing: {name!r}",
        "should_not_exist": "Name {name!r} already exists.",
    }

    def __init__(
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

        _exists = verify_timeperiod_name_exists(value)
        if self._should_exist and not _exists:
            raise self.make_error("should_exist", name=value)
        if not self._should_exist and _exists:
            raise self.make_error("should_not_exist", name=value)


class TimePeriodAlias(fields.String):
    """A field representing a time_period name"""

    default_error_messages = {
        "should_exist": "Timeperiod alias does not exist: {name!r}",
        "should_not_exist": "Timeperiod alias {name!r} already exists.",
    }

    def __init__(
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

        # Empty String because validation works for non-timeperiod alias & time period name is
        # verified separately
        _new_entry, _ = is_alias_used("timeperiods", "", value)
        if self._should_exist and _new_entry:
            raise self.make_error("should_exist", name=value)
        if not self._should_exist and not _new_entry:
            raise self.make_error("should_not_exist", name=value)


class TimeRange(BaseSchema):
    start = fields.String(
        required=True,
        format="time",
        example="14:00",
        description="The start time of the period's time range",
    )
    end = fields.String(
        required=True,
        format="time",
        example="16:00",
        description="The end time of the period's time range",
    )


class TimeRangeActive(BaseSchema):
    day = fields.String(
        description="The day for which time ranges are to be specified. The 'all' "
        "option allows to specify time ranges for all days.",
        pattern=f"all|{'|'.join(weekday_ids())}",
    )
    time_ranges = gui_fields.List(gui_fields.Nested(TimeRange))


class TimePeriodException(BaseSchema):
    date = fields.String(
        required=True,
        example="2020-01-01",
        format="date",
        description="The date of the time period exception." "8601 profile",
    )
    time_ranges = gui_fields.List(
        gui_fields.Nested(TimeRange),
        required=False,
        example=[{"start": "14:00", "end": "18:00"}],
    )


class InputTimePeriod(BaseSchema):
    name = TimePeriodName(
        example="first",
        description="A unique name for the time period.",
        required=True,
        should_exist=False,
    )
    alias = TimePeriodAlias(
        example="alias",
        description="An alias for the time period.",
        required=True,
        should_exist=False,
    )
    active_time_ranges = gui_fields.List(
        gui_fields.Nested(TimeRangeActive),
        example=[{"day": "monday", "time_ranges": [{"start": "12:00", "end": "14:00"}]}],
        description="The list of active time ranges.",
        required=True,
    )
    exceptions = gui_fields.List(
        gui_fields.Nested(TimePeriodException),
        required=False,
        example=[{"date": "2020-01-01", "time_ranges": [{"start": "14:00", "end": "18:00"}]}],
        description="A list of additional time ranges to be added.",
    )

    exclude = gui_fields.List(  # type: ignore[assignment]
        TimePeriodAlias(
            example="alias",
            description="The alias for a time period.",
            required=True,
            should_exist=True,
        ),
        example=["alias"],
        description="A list of time period aliases whose periods are excluded.",
        required=False,
    )


class UpdateTimePeriod(BaseSchema):
    alias = TimePeriodAlias(
        example="alias",
        description="An alias for the time period",
        required=False,
        should_exist=False,
    )
    active_time_ranges = gui_fields.List(
        gui_fields.Nested(TimeRangeActive),
        example=[
            {
                "day": "monday",
                "time_ranges": [{"start": "12:00", "end": "14:00"}],
            }
        ],
        description="The list of active time ranges which replaces the existing list of time ranges",
        required=False,
    )
    exceptions = gui_fields.List(
        gui_fields.Nested(TimePeriodException),
        required=False,
        example=[{"date": "2020-01-01", "time_ranges": [{"start": "14:00", "end": "18:00"}]}],
        description="A list of additional time ranges to be added.",
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
    host_name = MONITORED_HOST
    service_descriptions = gui_fields.List(
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
    service_descriptions = gui_fields.List(
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

    shared = gui_fields.List(
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

    shared = gui_fields.List(
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
    }

    def __init__(
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

        # TODO: change to names list only
        usernames = load_users()
        if self._should_exist and value not in usernames:
            raise self.make_error("should_exist", username=value)
        if not self._should_exist and value in usernames:
            raise self.make_error("should_not_exist", username=value)


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
    timerange = gui_fields.Nested(
        CustomTimeRange,
        description="A custom timerange during which notifications are disabled",
        required=False,
        example={
            "start_time": "2017-07-21T17:32:28Z",
            "end_time": "2017-07-21T18:32:28Z",
        },
    )


AUTH_PASSWORD = fields.String(
    required=False,
    description="The password for login",
    example="password",
)

AUTH_SECRET = fields.String(
    required=False,
    description="For accounts used by automation processes (such as fetching data from views "
    "for further procession). This is the automation secret",
    example="DEYQEQQPYCFFBYH@AVMC",
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


class AuthUpdateSecret(BaseSchema):
    auth_type = AUTH_UPDATE_TYPE
    secret = AUTH_SECRET


class AuthUpdatePassword(BaseSchema):
    auth_type = AUTH_UPDATE_TYPE
    password = AUTH_PASSWORD


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
    auth_option = gui_fields.Nested(
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
    contact_options = gui_fields.Nested(
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
    idle_timeout = gui_fields.Nested(
        IdleOption,
        required=False,
        description="Idle timeout for the user. Per default, the global configuration is used.",
        example={"option": "global"},
    )
    roles = gui_fields.List(
        fields.String(
            required=True,
            description="A role of the user",
            enum=["user", "admin", "guest"],
            example="user",
        ),
        required=False,
        load_default=list,
        description="The list of assigned roles to the user",
        example=["user"],
    )
    authorized_sites = gui_fields.List(
        gui_fields.SiteField(),
        description="The names of the sites the user is authorized to handle",
        example=["heute"],
        required=False,
    )
    contactgroups = gui_fields.List(
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
    disable_notifications = gui_fields.Nested(
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
    auth_option = gui_fields.Nested(
        AuthUpdateOption,
        required=False,
        description="Authentication option for the user",
        example={"auth_type": "password", "password": "password"},
        load_default=dict,
    )
    enforce_password_change = fields.Boolean(
        required=False,
        description="Enforce the password change on next login. This has no effect if you remove "
        "the authentication option",
        example=True,
    )
    disable_login = fields.Boolean(
        required=False,
        description="The user can be blocked from login but will remain part of the site. "
        "The disabling does not affect notification and alerts.",
        example=False,
        attribute="locked",
    )
    contact_options = gui_fields.Nested(
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
    idle_timeout = gui_fields.Nested(
        IdleOption,
        required=False,
        description="Idle timeout for the user",
        example={},
    )
    roles = gui_fields.List(
        fields.String(
            required=False,
            description="A role of the user",
            enum=["user", "admin", "guest"],
            example="user",
        ),
        required=False,
        description="The list of assigned roles to the user",
        example=["user"],
    )
    authorized_sites = gui_fields.List(
        gui_fields.SiteField(),
        description="The names of the sites the user is authorized to handle",
        example=["heute"],
        required=False,
    )
    contactgroups = gui_fields.List(
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
    disable_notifications = gui_fields.Nested(
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


class Tags(gui_fields.List):
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


class AuxTag(fields.String):
    default_error_messages = {
        "invalid": "The specified auxiliary tag id is not valid: {name!r}",
    }

    def __init__(
        self,
        example,
        required=True,
        validate=None,
        **kwargs,
    ):
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)
        available_aux_tags = load_aux_tags()
        if value not in available_aux_tags:
            raise self.make_error("invalid", name=value)


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
    aux_tags = gui_fields.List(
        AuxTag(
            example="ip-v4",
            description="An auxiliary tag id",
            required=False,
        ),
        description="The list of auxiliary tag ids. Built-in tags (ip-v4, ip-v6, snmp, tcp, ping) and custom defined tags are allowed.",
        example=["ip-v4, ip-v6"],
        required=False,
        load_default=list,
    )


class InputHostTagGroup(BaseSchema):
    ident = HostTagGroupId(
        example="group_id",
        description="An id for the host tag group",
        attribute="id",
        pattern="[a-zA-Z_]+[-0-9a-zA-Z_]*",
    )
    title = fields.String(
        required=True,
        example="Kubernetes",
        description="A title for the host tag",
    )
    topic = fields.String(
        required=True,
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
        gui_fields.Nested(HostTag),
        required=True,
        example=[{"ident": "pod", "title": "Pod"}],
        description="A list of host tags belonging to the host tag group",
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
        gui_fields.Nested(HostTag),
        required=False,
        example=[{"ident": "pod", "title": "Pod"}],
        description="A list of host tags belonging to the host tag group",
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
    entries = gui_fields.List(
        SERVICE_DESCRIPTION_FIELD,
        required=True,
        example=["CPU utilization", "Memory"],
    )


class BulkDeleteDowntime(BaseSchema):
    host_name = MONITORED_HOST
    entries = gui_fields.List(
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
    entries = gui_fields.List(
        EXISTING_HOST_NAME,
        required=True,
        example=["example", "sample"],
        description="A list of host names.",
    )


class BulkDeleteFolder(BaseSchema):
    entries = gui_fields.List(
        EXISTING_FOLDER,
        required=True,
        example=["production", "secondproduction"],
    )


class BulkDeleteHostGroup(BaseSchema):
    entries = gui_fields.List(
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
    entries = gui_fields.List(
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
    entries = gui_fields.List(
        fields.String(
            required=True,
            description="The name of the contact group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
        description="A list of contract group names.",
    )


class ActivateChanges(BaseSchema):
    redirect = fields.Boolean(
        description=(
            "After starting the activation, redirect immediately to the 'Wait for completion' "
            "endpoint instead of waiting for the completion."
        ),
        required=False,
        load_default=False,
        example=False,
    )
    sites = gui_fields.List(
        gui_fields.SiteField(),
        description=(
            "The names of the sites on which the configuration shall be activated."
            " An empty list means all sites which have pending changes."
        ),
        required=False,
        load_default=list,
        example=["production"],
    )
    force_foreign_changes = fields.Boolean(
        description=param_description(
            watolib.activate_changes_start.__doc__, "force_foreign_changes"
        ),
        required=False,
        load_default=False,
        example=False,
    )


class X509ReqPEM(BaseSchema):
    csr = gui_fields.X509ReqPEMField(
        required=True,
        example="-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----\n",
        description="PEM-encoded X.509 CSR.",
    )
