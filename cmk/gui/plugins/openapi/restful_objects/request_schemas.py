#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from marshmallow import ValidationError  # type: ignore[import]
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.gui import watolib
from cmk.utils.defines import weekday_ids
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.livestatus_helpers.commands.downtimes import (
    schedule_host_downtime,
    schedule_hostgroup_host_downtime,
    schedule_service_downtime,
    schedule_servicegroup_service_downtime,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME_REGEXP
from cmk.gui.plugins.openapi.utils import param_description, BaseSchema
from cmk.gui.plugins.openapi.livestatus_helpers.commands.acknowledgments import (
    acknowledge_host_problem,
    acknowledge_service_problem,
)
from cmk.gui.plugins.webapi import validate_host_attributes
from cmk.gui.plugins.openapi.endpoints.utils import verify_group_exist
from cmk.gui.watolib.timeperiods import verify_timeperiod_name_exists
from cmk.gui.watolib.groups import is_alias_used
from cmk.gui.watolib.passwords import password_exists, contact_group_choices

import cmk.gui.config as config


class InputAttribute(BaseSchema):
    key = fields.String(required=True)
    value = fields.String(required=True)


class Hostname(fields.String):
    """A field representing a hostname.

    """
    default_error_messages = {
        'should_exist': 'Host missing: {host_name!r}',
        'should_not_exist': 'Host {host_name!r} already exists.',
    }

    def __init__(
        self,
        example='example.com',
        pattern=HOST_NAME_REGEXP,
        required=True,
        validate=None,
        should_exist: bool = True,
        **kwargs,
    ):
        self._should_exist = should_exist
        super().__init__(
            example=example,
            pattern=pattern,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        host = watolib.Host.host(value)
        if self._should_exist and not host:
            self.fail("should_exist", host_name=value)
        elif not self._should_exist and host:
            self.fail("should_not_exist", host_name=value)


EXISTING_HOST_NAME = Hostname(
    description="The hostname or IP address itself.",
    required=True,
    should_exist=True,
)

MONITORED_HOST = fields.String(
    description="The hostname or IP address itself.",
    example='example.com',
    pattern=HOST_NAME_REGEXP,
    required=True,
)


class FolderField(fields.String):
    """This field represents a WATO Folder.

    It will return a Folder instance, ready to use.
    """
    default_error_messages = {
        'not_found': "The folder {folder_id!r} could not be found.",
    }
    pattern = "[a-fA-F0-9]{32}|root"

    def _deserialize(self, value, attr, data):
        value = super()._deserialize(value, attr, data)
        try:
            if value == 'root':
                folder = watolib.Folder.root_folder()
            else:
                folder = watolib.Folder.by_id(value)
            return folder
        except MKUserError:
            if self.required:
                self.fail("not_found", folder_id=value)


class AttributesField(fields.Dict):
    default_error_messages = {
        'attribute_forbidden': "Setting of attribute {attribute!r} is forbidden: {value!r}.",
    }

    def _validate(self, value):
        # Special keys:
        #  - site -> validate against config.allsites().keys()
        #  - tag_* -> validate_host_tags
        #  - * -> validate against host_attribute_registry.keys()
        try:
            validate_host_attributes(value, new=True)
            if 'meta_data' in value:
                self.fail("attribute_forbidden", attribute='meta_data', value=value)
        except MKUserError as exc:
            raise ValidationError(str(exc))


EXISTING_FOLDER = FolderField(
    description=("The folder-id of the folder under which this folder shall be created. May be "
                 "'root' for the root-folder."),
    pattern="[a-fA-F0-9]{32}|root",
    example="root",
    required=True,
)

NAME_FIELD = fields.String(
    required=True,
    description="A name used as identifier",
    example='windows',
)

SERVICEGROUP_NAME = fields.String(
    required=True,
    description=param_description(schedule_servicegroup_service_downtime.__doc__,
                                  'servicegroup_name'),
    example='Webservers',
)


class CreateHost(BaseSchema):
    """Creating a new host

    Required arguments:

      * `host_name` - A host name with or without domain part. IP addresses are also allowed.
      * `folder` - The folder identifier.

    Optional arguments:

      * `attributes`
      * `nodes`
    """
    host_name = Hostname(
        description="The hostname or IP address of the host to be created.",
        required=True,
        should_exist=False,
    )
    folder = EXISTING_FOLDER
    attributes = AttributesField(
        description="Attributes to set on the newly created host.",
        example={'ipaddress': '192.168.0.123'},
        missing=dict,
    )
    nodes = fields.List(EXISTING_HOST_NAME,
                        description="Nodes where the newly created host should be the "
                        "cluster-container of.",
                        required=False,
                        missing=list,
                        example=["host1", "host2", "host3"])


class BulkCreateHost(BaseSchema):
    entries = fields.List(
        fields.Nested(CreateHost),
        example=[{
            "host_name": "example.com",
            "folder": "root",
            "attributes": {},
            "nodes": ["host1", "host2"],
        }],
        uniqueItems=True,
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
    attributes = AttributesField(
        description=("Replace all currently set attributes on the host, with these attributes. "
                     "Any previously set attributes which are not given here will be removed."),
        example={'ipaddress': '192.168.0.123'},
        missing=dict,
        required=False,
    )
    update_attributes = AttributesField(
        description=("Just update the hosts attributes with these attributes. The previously set "
                     "attributes will not be touched."),
        example={'ipaddress': '192.168.0.123'},
        missing=dict,
        required=False,
    )
    nodes = fields.List(
        EXISTING_HOST_NAME,
        description="Nodes where the host should be the cluster-container of.",
        example=["host1", "host2", "host3"],
        missing=list,
        required=False,
    )


class UpdateHostEntry(BaseSchema):
    host_name = EXISTING_HOST_NAME
    attributes = AttributesField(
        description=("Replace all currently set attributes on the host, with these attributes. "
                     "Any previously set attributes which are not given here will be removed."),
        example={'ipaddress': '192.168.0.123'},
        missing=dict,
        required=False,
    )
    update_attributes = AttributesField(
        description=("Just update the hosts attributes with these attributes. The previously set "
                     "attributes will not be touched."),
        example={'ipaddress': '192.168.0.123'},
        missing=dict,
        required=False,
    )
    nodes = fields.List(
        EXISTING_HOST_NAME,
        description="Nodes where the host should be the cluster-container of.",
        example=["host1", "host2", "host3"],
        missing=list,
        required=False,
    )


class BulkUpdateHost(BaseSchema):
    entries = fields.List(
        fields.Nested(UpdateHostEntry),
        example=[{
            "host_name": "example.com",
            "attributes": {}
        }],
    )


class Group(fields.String):
    """A field representing a group.

    """
    default_error_messages = {
        'should_exist': 'Group missing: {name!r}',
        'should_not_exist': 'Group {name!r} already exists.',
    }

    def __init__(
        self,
        group_type,
        example,
        required=True,
        validate=None,
        should_exist: bool = True,
        **kwargs,
    ):
        self._group_type = group_type
        self._should_exist = should_exist
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        group_exists = verify_group_exist(self._group_type, value)
        if self._should_exist and not group_exists:
            self.fail("should_exist", name=value)
        elif not self._should_exist and group_exists:
            self.fail("should_not_exist", name=value)


EXISTING_HOST_GROUP_NAME = Group(
    group_type="host",
    example="windows",
    required=True,
    description="The name of the host group.",
    should_exist=True,
)

EXISTING_SERVICE_GROUP_NAME = Group(
    group_type="service",
    example="windows",
    required=True,
    description="The name of the service group.",
    should_exist=True,
)


class InputHostGroup(BaseSchema):
    """Creating a host group"""
    name = NAME_FIELD
    alias = fields.String(example="Windows Servers")


class BulkInputHostGroup(BaseSchema):
    """Bulk creating host groups"""
    entries = fields.List(
        fields.Nested(InputHostGroup),
        example=[{
            'name': 'windows',
            'alias': 'Windows Servers',
        }],
        uniqueItems=True,
    )


class UpdateHostGroup(BaseSchema):
    """Updating a host group"""
    name = EXISTING_HOST_GROUP_NAME
    attributes = fields.Nested(InputHostGroup)


class BulkUpdateHostGroup(BaseSchema):
    """Bulk update host groups"""
    entries = fields.List(fields.Nested(UpdateHostGroup),
                          example=[{
                              'name': 'windows',
                              'attributes': {
                                  'name': 'windows updated',
                                  'alias': 'Windows Servers',
                              },
                          }])


class InputContactGroup(BaseSchema):
    """Creating a contact group"""
    name = fields.String(required=True, example="OnCall")
    alias = fields.String(example="Not on Sundays.")


class BulkInputContactGroup(BaseSchema):
    """Bulk creating contact groups"""
    # TODO: add unique entries attribute
    entries = fields.List(
        fields.Nested(InputContactGroup),
        example=[{
            "name": "OnCall",
            "alias": "Not on Sundays",
        }],
        uniqueItems=True,
    )


class UpdateContactGroup(BaseSchema):
    """Updating a contact group"""
    name = Group(
        group_type="contact",
        description="The name of the contact group.",
        example="OnCall",
        required=True,
        should_exist=True,
    )
    attributes = fields.Nested(InputContactGroup)


class BulkUpdateContactGroup(BaseSchema):
    """Bulk update contact groups"""
    entries = fields.List(fields.Nested(UpdateContactGroup),
                          example=[{
                              'name': 'OnCall',
                              'attributes': {
                                  'name': 'OnCall updated',
                                  'alias': 'Not on Sundays',
                              },
                          }])


class InputServiceGroup(BaseSchema):
    """Creating a service group"""
    name = NAME_FIELD
    alias = fields.String(example="Environment Sensors")


class BulkInputServiceGroup(BaseSchema):
    """Bulk creating service groups"""
    entries = fields.List(
        fields.Nested(InputServiceGroup),
        example=[{
            "name": "environment",
            "alias": "Environment Sensors",
        }],
        uniqueItems=True,
    )


class UpdateServiceGroup(BaseSchema):
    """Updating a service group"""
    name = EXISTING_SERVICE_GROUP_NAME
    attributes = fields.Nested(InputServiceGroup)


class BulkUpdateServiceGroup(BaseSchema):
    """Bulk update service groups"""
    entries = fields.List(fields.Nested(UpdateServiceGroup),
                          example=[{
                              'name': 'windows',
                              'attributes': {
                                  'name': 'windows updated',
                                  'alias': 'Windows Servers',
                              },
                          }])


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
        [Host Administration chapter of the handbook](https://checkmk.com/cms_wato_hosts.html#Introduction).
    """
    name = fields.String(description="The name of the folder.", required=True, example="production")
    title = fields.String(
        required=True,
        example="Production Hosts",
    )
    parent = FolderField(
        description=("The folder-id of the folder under which this folder shall be created. May be "
                     "'root' for the root-folder."),
        pattern="[a-fA-F0-9]{32}|root",
        example="root",
        required=True,
    )
    attributes = AttributesField(
        description=("Specific attributes to apply for all hosts in this folder "
                     "(among other things)."),
        missing=dict,
        example={},
    )


class BulkCreateFolder(BaseSchema):
    entries = fields.List(
        fields.Nested(CreateFolder),
        example=[{
            "name": "production",
            "parent": "root",
            "attributes": {
                "foo": "bar"
            },
        }],
        uniqueItems=True,
    )


class UpdateFolder(BaseSchema):
    """Updating a folder"""
    title = fields.String(
        example="Virtual Servers.",
        required=True,
    )
    attributes = AttributesField(
        description=("Replace all attributes with the ones given in this field. Already set"
                     "attributes, not given here, will be removed."),
        example={},
        missing=dict,
        required=False,
    )
    update_attributes = AttributesField(
        description=("Only set the attributes which are given in this field. Already set "
                     "attributes will not be touched."),
        example={},
        missing=dict,
        required=False,
    )


class UpdateFolderEntry(UpdateFolder):
    folder = EXISTING_FOLDER
    title = fields.String(required=True, example="Virtual Servers")
    attributes = AttributesField(
        description=("Replace all attributes with the ones given in this field. Already set"
                     "attributes, not given here, will be removed."),
        example={},
        missing=dict,
        required=False,
    )
    update_attributes = AttributesField(
        description=("Only set the attributes which are given in this field. Already set "
                     "attributes will not be touched."),
        example={},
        missing=dict,
        required=False,
    )


class BulkUpdateFolder(BaseSchema):
    entries = fields.Nested(UpdateFolderEntry,
                            many=True,
                            example=[{
                                'ident': 'root',
                                'title': 'Virtual Servers',
                                'attributes': {
                                    'key': 'foo'
                                }
                            }])


class CreateDowntimeBase(BaseSchema):
    downtime_type = fields.String(
        required=True,
        description="The type of downtime to create.",
        enum=['host', 'service', 'hostgroup', 'servicegroup'],
        example="host",
    )
    start_time = fields.DateTime(
        format="iso8601",
        required=True,
        example="2017-07-21T17:32:28Z",
        description=
        "The start datetime of the new downtime. The format has to conform to the ISO 8601 profile",
    )
    end_time = fields.DateTime(
        required=True,
        example="2017-07-21T17:32:28Z",
        description=
        "The end datetime of the new downtime. The format has to conform to the ISO 8601 profile",
        format="iso8601",
    )
    recur = fields.String(
        required=False,
        enum=[
            "fixed", "hour", "day", "week", "second_week", "fourth_week", "weekday_start",
            "weekday_end", "day_of_month"
        ],
        description=param_description(schedule_host_downtime.__doc__, 'recur'),
        example="hour",
        missing="fixed",
    )
    duration = fields.Integer(
        required=False,
        description=param_description(schedule_host_downtime.__doc__, 'duration'),
        example=3600,
        missing=0,
    )
    comment = fields.String(required=False, example="Security updates")


class TimePeriodName(fields.String):
    """A field representing a time_period name"""

    default_error_messages = {
        'should_exist': 'Name missing: {name!r}',
        'should_not_exist': 'Name {name!r} already exists.',
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
            self.fail("should_exist", name=value)
        elif not self._should_exist and _exists:
            self.fail("should_not_exist", name=value)


class TimePeriodAlias(fields.String):
    """A field representing a time_period name"""

    default_error_messages = {
        'should_exist': 'Alias missing: {name!r}',
        'should_not_exist': 'Alias {name!r} already exists.',
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
            self.fail("should_exist", name=value)
        elif not self._should_exist and not _new_entry:
            self.fail("should_not_exist", name=value)


class TimeRange(BaseSchema):
    start = fields.Time(
        required=True,
        example="14:00",
        description="The start time of the period's time range",
    )
    end = fields.Time(
        required=True,
        example="16:00",
        description="The end time of the period's time range",
    )


class TimeRangeActive(BaseSchema):
    day = fields.String(description="The day for which time ranges are to be specified. The 'all' "
                        "option allows to specify time ranges for all days.",
                        pattern=f"all|{'|'.join(weekday_ids())}")
    time_ranges = fields.List(fields.Nested(TimeRange))


class TimePeriodException(BaseSchema):
    date = fields.Date(
        required=True,
        example="2020-01-01",
        description="The date of the time period exception."
        "8601 profile",
    )
    time_ranges = fields.List(
        fields.Nested(TimeRange),
        required=False,
        example=[{
            'start': '14:00',
            'end': '18:00'
        }],
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
    active_time_ranges = fields.List(
        fields.Nested(TimeRangeActive),
        example=[{
            'day': 'monday',
            'time_ranges': [{
                'start': '12:00',
                'end': '14:00'
            }]
        }],
        description="The list of active time ranges.",
        required=True,
    )
    exceptions = fields.List(
        fields.Nested(TimePeriodException),
        required=False,
        example=[{
            'date': '2020-01-01',
            'time_ranges': [{
                'start': '14:00',
                'end': '18:00'
            }]
        }],
    )

    exclude = fields.List(
        TimePeriodAlias(
            example="alias",
            description="The alias for a time period.",
            required=True,
            should_exist=True,
        ),
        example="['alias']",
        description="The collection of time period aliases whose periods are excluded",
        required=False,
    )


class UpdateTimePeriod(BaseSchema):
    alias = TimePeriodAlias(
        example="alias",
        description="An alias for the time period",
        required=False,
        should_exist=False,
    )
    active_time_ranges = fields.List(
        fields.Nested(TimeRangeActive),
        example={
            'start': '12:00',
            'end': '14:00'
        },
        description="The list of active time ranges which replaces the existing list of time ranges",
        required=False,
    )
    exceptions = fields.List(
        fields.Nested(TimePeriodException),
        required=False,
        example=[{
            'date': '2020-01-01',
            'time_ranges': [{
                'start': '14:00',
                'end': '18:00'
            }]
        }],
    )


SERVICE_DESCRIPTION_FIELD = fields.String(required=False, example="CPU utilization")

HOST_DURATION = fields.Integer(
    required=False,
    description=param_description(schedule_host_downtime.__doc__, 'duration'),
    example=3600,
    missing=0,
)


class CreateHostDowntime(CreateDowntimeBase):
    host_name = MONITORED_HOST
    duration = HOST_DURATION
    include_all_services = fields.Boolean(
        required=False,
        description=param_description(schedule_host_downtime.__doc__, 'include_all_services'),
        example=False,
        missing=False,
    )


class CreateServiceDowntime(CreateDowntimeBase):
    host_name = MONITORED_HOST
    service_descriptions = fields.List(
        fields.String(),
        uniqueItems=True,
        required=True,
        example=["CPU utilization", "Memory"],
        description=param_description(schedule_service_downtime.__doc__, 'service_description'),
    )
    duration = fields.Integer(
        required=False,
        description=param_description(schedule_service_downtime.__doc__, 'duration'),
        example=3600,
        missing=0,
    )


class CreateServiceGroupDowntime(CreateDowntimeBase):
    servicegroup_name = SERVICEGROUP_NAME
    include_hosts = fields.Boolean(
        required=False,
        description=param_description(schedule_servicegroup_service_downtime.__doc__,
                                      'include_hosts'),
        example=False,
        missing=False,
    )
    duration = HOST_DURATION


class CreateHostGroupDowntime(CreateDowntimeBase):
    hostgroup_name = fields.String(
        required=True,
        description=param_description(schedule_hostgroup_host_downtime.__doc__, 'hostgroup_name'),
        example='Servers',
    )
    include_all_services = fields.Boolean(
        required=False,
        description=param_description(schedule_hostgroup_host_downtime.__doc__,
                                      'include_all_services'),
        example=False,
        missing=False,
    )
    duration = HOST_DURATION


class CreateDowntime(OneOfSchema):
    type_field = 'downtime_type'
    type_field_remove = False
    type_schemas = {
        'host': CreateHostDowntime,
        'hostgroup': CreateHostGroupDowntime,
        'service': CreateServiceDowntime,
        'servicegroup': CreateServiceGroupDowntime,
    }


class PasswordIdent(fields.String):
    """A field representing a password identifier"""

    default_error_messages = {
        'should_exist': 'Identifier missing: {name!r}',
        'should_not_exist': 'Identifier {name!r} already exists.',
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

        exists = password_exists(value)
        if self._should_exist and not exists:
            self.fail("should_exist", name=value)
        elif not self._should_exist and exists:
            self.fail("should_not_exist", name=value)


class PasswordOwner(fields.String):
    """A field representing a password owner group"""

    default_error_messages = {
        'invalid': 'Specified owner value is not valid: {name!r}',
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
        """Verify if the specified owner is valid for the logged-in user

        Non-admin users cannot specify admin as the owner

        """
        super()._validate(value)
        permitted_owners = [group[0] for group in contact_group_choices(only_own=True)]
        if config.user.may("wato.edit_all_passwords"):
            permitted_owners.append("admin")

        if value not in permitted_owners:
            self.fail("invalid", name=value)


class PasswordShare(fields.String):
    """A field representing a password share group"""

    default_error_messages = {
        'invalid': 'The password cannot be shared with specified group: {name!r}',
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
        shareable_groups = [group[0] for group in contact_group_choices()]
        if value not in ["all", *shareable_groups]:
            self.fail("invalid", name=value)


class InputPassword(BaseSchema):
    ident = PasswordIdent(
        example="pass",
        description="An unique identifier for the password",
        should_exist=False,
    )
    title = fields.String(
        required=True,
        example="Kubernetes login",
        description="A title for the password",
    )
    comment = fields.String(required=False,
                            example="Kommentar",
                            description="A comment for the password",
                            missing="")

    documentation_url = fields.String(
        required=False,
        attribute="docu_url",
        example="localhost",
        description=
        "An optional URL pointing to documentation or any other page. You can use either global URLs (beginning with http://), absolute local urls (beginning with /) or relative URLs (that are relative to check_mk/).",
        missing="",
    )

    password = fields.String(
        required=True,
        example="password",
        description="The password string",
    )

    owner = PasswordOwner(
        example="admin",
        description=
        "Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        required=True,
        attribute="owned_by",
    )

    shared = fields.List(
        PasswordShare(
            example="all",
            description=
            "By default only the members of the owner contact group are permitted to use a a configured password. It is possible to share a password with other groups of users to make them able to use a password in checks.",
        ),
        example=["all"],
        description="The list of members to share the password with",
        required=False,
        attribute="shared_with",
        missing=[],
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
        description=
        "An optional URL pointing to documentation or any other page. You can use either global URLs (beginning with http://), absolute local urls (beginning with /) or relative URLs (that are relative to check_mk/).",
    )

    password = fields.String(
        required=False,
        example="password",
        description="The password string",
    )

    owner = PasswordOwner(
        example="admin",
        description=
        "Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        required=False,
        attribute="owned_by")

    shared = fields.List(PasswordShare(
        example="all",
        description=
        "By default only the members of the owner contact group are permitted to use a a configured password. It is possible to share a password with other groups of users to make them able to use a password in checks.",
    ),
                         example=["all"],
                         description="The list of members to share the password with",
                         required=False,
                         attribute="shared_with")


class AcknowledgeHostProblem(BaseSchema):
    sticky = fields.Boolean(
        required=False,
        missing=False,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, 'sticky'),
    )

    persistent = fields.Boolean(
        required=False,
        missing=False,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, 'persistent'),
    )

    notify = fields.Boolean(
        required=False,
        missing=False,
        example=False,
        description=param_description(acknowledge_host_problem.__doc__, 'notify'),
    )

    comment = fields.String(
        required=False,
        missing="Acknowledged",
        example='This was expected.',
        description=param_description(acknowledge_host_problem.__doc__, 'comment'),
    )


class BulkAcknowledgeHostProblem(AcknowledgeHostProblem):
    entries = fields.List(
        MONITORED_HOST,
        required=True,
        example=["example.com", "sample.com"],
    )


SERVICE_STICKY_FIELD = fields.Boolean(
    required=False,
    missing=False,
    example=False,
    description=param_description(acknowledge_service_problem.__doc__, 'sticky'),
)

SERVICE_PERSISTENT_FIELD = fields.Boolean(
    required=False,
    missing=False,
    example=False,
    description=param_description(acknowledge_service_problem.__doc__, 'persistent'),
)

SERVICE_NOTIFY_FIELD = fields.Boolean(
    required=False,
    missing=False,
    example=False,
    description=param_description(acknowledge_service_problem.__doc__, 'notify'),
)

SERVICE_COMMENT_FIELD = fields.String(
    required=False,
    missing="Acknowledged",
    example='This was expected.',
    description=param_description(acknowledge_service_problem.__doc__, 'comment'),
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
    )


class BulkDeleteHost(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        EXISTING_HOST_NAME,
        required=True,
        example=["example", "sample"],
    )


class BulkDeleteFolder(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        EXISTING_FOLDER,
        required=True,
        example=["production", "secondproduction"],
    )


class BulkDeleteHostGroup(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the host group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
    )


class BulkDeleteServiceGroup(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the service group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
    )


class BulkDeleteContactGroup(BaseSchema):
    # TODO: addition of etag field
    entries = fields.List(
        fields.String(
            required=True,
            description="The name of the contact group config",
            example="windows",
        ),
        required=True,
        example=["windows", "panels"],
    )
