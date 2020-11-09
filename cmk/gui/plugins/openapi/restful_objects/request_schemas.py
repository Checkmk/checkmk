#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import urllib.parse

from marshmallow import ValidationError
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.gui import watolib, config
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
from cmk.gui.watolib.tags import load_tag_config, load_aux_tags


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


EXISTING_FOLDER = fields.FolderField(
    description=("The folder-id of the folder under which this folder shall be created. May be "
                 "'root' for the root-folder."),
    example="/",
    required=True,
)

GROUP_NAME_FIELD = fields.String(
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


class CreateClusterHost(BaseSchema):
    host_name = Hostname(
        description="The hostname of the cluster host.",
        required=True,
        should_exist=False,
    )
    folder = EXISTING_FOLDER
    attributes = AttributesField(
        description="Attributes to set on the newly created host.",
        example={'ipaddress': '192.168.0.123'},
        missing=dict,
    )
    nodes = fields.List(
        EXISTING_HOST_NAME,
        description="Nodes where the newly created host should be the cluster-container of.",
        required=True,
        example=["host1", "host2", "host3"],
    )


class UpdateNodes(BaseSchema):
    nodes = fields.List(
        EXISTING_HOST_NAME,
        description="Nodes where the newly created host should be the cluster-container of.",
        required=True,
        example=["host1", "host2", "host3"],
    )


class CreateHost(BaseSchema):
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


class BulkCreateHost(BaseSchema):
    entries = fields.List(
        fields.Nested(CreateHost),
        example=[{
            "host_name": "example.com",
            "folder": "root",
            "attributes": {},
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
    remove_attributes = fields.List(
        fields.String(),
        description="A list of attributes which should be removed.",
        example=["tag_foobar"],
        missing=[],
        required=False,
    )


class UpdateHostEntry(UpdateHost):
    host_name = EXISTING_HOST_NAME


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
    name = GROUP_NAME_FIELD
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
    name = GROUP_NAME_FIELD
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
    name = fields.String(
        description=("The filesystem directory name (not path!) of the folder."
                     " No slashes are allowed."),
        required=True,
        pattern="[^/]+",
        example="production",
    )
    title = fields.String(
        required=True,
        description="The folder title as displayed in the user interface.",
        example="Production Hosts",
    )
    parent = fields.FolderField(
        required=True,
        description=("The folder in which the new folder shall be placed in. The root-folder is "
                     "specified by '/'."),
        example="/",
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


class MoveFolder(BaseSchema):
    destination = fields.FolderField(
        required=True,
        description="Where the folder has to be moved to.",
        example=urllib.parse.quote_plus('/my/fine/folder'),
    )


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
        'should_exist': 'Timeperiod alias does not exist: {name!r}',
        'should_not_exist': 'Timeperiod alias {name!r} already exists.',
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

    exclude = fields.List(  # type: ignore[assignment]
        TimePeriodAlias(
            example="alias",
            description="The alias for a time period.",
            required=True,
            should_exist=True,
        ),
        example=["alias"],
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
    duration = HOST_DURATION


class CreateHostGroupDowntime(CreateDowntimeBase):
    hostgroup_name = fields.String(
        required=True,
        description=param_description(schedule_hostgroup_host_downtime.__doc__, 'hostgroup_name'),
        example='Servers',
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


class HostTagGroupId(fields.String):
    """A field representing a host tag group id"""

    default_error_messages = {
        'invalid': 'The specified tag group id is already in use: {name!r}',
    }

    def _validate(self, value):
        super()._validate(value)
        host_tag_group_config = load_tag_config()
        if not host_tag_group_config.valid_id(value):
            self.fail("invalid", name=value)


class Tags(fields.List):
    """A field representing a tags list"""

    default_error_messages = {
        'duplicate': 'Tags IDs must be unique. You\'ve used the following at least twice: {name!r}',
        'invalid_none': 'Cannot use an empty tag ID for single entry',
        'multi_none': 'Only one tag id is allowed to be empty'
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
                    self.fail("invalid_none")

                if none_tag_exists:
                    self.fail("multi_none")

                none_tag_exists = True

    def _unique_ids(self, tags):
        seen_ids = set()
        for tag in tags:
            tag_id = tag.get("id")
            if tag_id in seen_ids:
                self.fail("duplicate", name=tag_id)
            seen_ids.add(tag_id)


class AuxTag(fields.String):
    default_error_messages = {
        'invalid': 'The specified auxiliary tag id is not valid: {name!r}',
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
            self.fail("invalid", name=value)


class HostTag(BaseSchema):
    ident = fields.String(required=False,
                          example="tag_id",
                          description="An unique id for the tag",
                          missing=None,
                          attribute="id")
    title = fields.String(
        required=True,
        example="Tag",
        description="The title of the tag",
    )
    aux_tags = fields.List(
        AuxTag(
            example="ip-v4",
            description="An auxiliary tag id",
            required=False,
        ),
        description=
        "The list of auxiliary tag ids. Built-in tags (ip-v4, ip-v6, snmp, tcp, ping) and custom defined tags are allowed.",
        example=["ip-v4, ip-v6"],
        required=False,
        missing=[],
    )


class InputHostTagGroup(BaseSchema):
    ident = HostTagGroupId(
        example="group_id",
        description="An id for the host tag group",
        attribute="id",
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
        missing="",
    )
    tags = Tags(
        fields.Nested(HostTag),
        required=True,
        example=[{
            "ident": "pod",
            "title": "Pod"
        }],
        description="A list of host tags belonging to the host tag group",
    )


class DeleteHostTagGroup(BaseSchema):
    repair = fields.Boolean(
        required=False,
        missing=False,
        example=False,
        description=
        "The host tag group can still be in use. Setting repair to True gives permission to automatically remove the tag from the affected hosts."
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
        example=[{
            "ident": "pod",
            "title": "Pod"
        }],
        description="A list of host tags belonging to the host tag group",
    )
    repair = fields.Boolean(
        required=False,
        missing=False,
        example=False,
        description=
        "The host tag group can be in use by other hosts. Setting repair to True gives permission to automatically update the tag from the affected hosts."
    )


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


class ActivateChanges(BaseSchema):
    redirect = fields.Boolean(
        description="Redirect immediately to the 'Wait for completion' endpoint.",
        required=False,
        missing=False,
        example=False,
    )
    sites = fields.List(
        fields.String(),
        description=("On which sites the configuration shall be activated. An empty list "
                     "means all sites which have pending changes."),
        required=False,
        missing=[],
        example=['production'],
    )
