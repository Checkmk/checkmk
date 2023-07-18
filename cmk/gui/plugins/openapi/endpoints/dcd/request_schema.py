#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from marshmallow_oneofschema import OneOfSchema

import cmk.gui.cee.plugins.watolib.dcd as dcd_store
from cmk.gui import fields as gui_fields
from cmk.gui.fields.definitions import FolderField
from cmk.gui.fields.utils import BaseSchema

from cmk import fields
from cmk.fields import base


class TimeIntervalAttribute(BaseSchema):
    start = fields.Time(required=True, description="Starting time interval", example="11:30")
    end = fields.Time(required=True, description="Ending time interval", example="15:45")


class CreationRuleAttribute(BaseSchema):
    folder_path = FolderField(
        required=False,
        description="Name of the folder the connection creates hosts in. Once created, you can choose to move the host to another folder.",
        example="/folder_1/subfolder_a",
        load_default="/",
    )

    host_attributes = gui_fields.host_attributes_field(
        "host",
        "create",
        "inbound",
        description="Attributes to set on the newly created host.",
        example={"ipaddress": "192.168.0.123"},
        required=False,
        load_default={
            "tag_snmp_ds": "no-snmp",
            "tag_agent": "no-agent",
            "tag_piggyback": "piggyback",
            "tag_address_family": "no-ip",
        },
    )

    delete_hosts = fields.Boolean(
        required=False,
        load_default=False,
        description="Delete the hosts created by this connection whose piggyback data is no longer present.",
        example=False,
    )

    matching_hosts = fields.List(
        gui_fields.HostField,
        required=False,
        description="Restrict host creation using regular expressions",
        example=["host1", "host2", "host3"],
    )


class DcdIdField(base.String):
    default_error_messages = {
        "should_exist": "Cannot find a dynamic host configuration with ID: {dcd_id!r}",
        "should_not_exist": "ID {dcd_id!r} already in use",
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
            pattern="^[-0-9a-zA-Z_.]+$",
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        dcds = dcd_store.read_dcds()

        if value in dcds and not self._should_exist:
            raise self.make_error("should_not_exist", dcd_id=value)

        if value not in dcds and self._should_exist:
            raise self.make_error("should_exist", dcd_id=value)


class BaseCreateDCD(BaseSchema):
    dcd_id = DcdIdField(
        description="The unique ID of the Piggyback dynamic host configuration to be created.",
        example="MyDcd01",
        required=True,
        should_exist=False,
    )

    title = fields.String(
        required=True,
        description="Name your connection for easy recognition.",
        example="My fancy piggyback dynamic host configuration",
    )

    comment = fields.String(
        required=False,
        description="Add a comment to your Piggyback dynamic host configuration",
        example="This rule updates the host configuration from Initech cloud provider.",
        load_default="",
    )

    documentation_url = fields.URL(
        required=False,
        description="Add a URL linking to a documentation or any other page. You can use either global URLs (starting with http://), absolute local URLs (starting with /) or relative URLs (relative to check_mk/).",
        example="https://example.com/doc",
        load_default="",
    )

    disabled = fields.Boolean(
        required=False,
        load_default=False,
        description="The Piggyback dynamic host configuration can be disabled but will remain part of the site.",
        example=False,
    )

    site = gui_fields.SiteField(
        required=True,
        example="global",
        description="Specify the site where you want this connector to run. Only this site will process the piggyback data.",
    )

    connector_type = fields.String(
        required=True,
        description="The name of the plugin to be used. Currently only piggyback is supported",
        enum=["piggyback"],
        example="piggyback",
    )


class CreatePiggybackDCD(BaseCreateDCD):
    restrict_source_hosts = fields.List(
        gui_fields.HostField(
            should_exist=True,
        ),
        required=False,
        description="Only care about hosts that receive piggyback data from hosts which name matches one of these regular expressions",
        example=["host1", "host2", "host3"],
    )

    interval = fields.Integer(
        description="The interval in seconds the connection will be executed to check the available piggyback and update the configuration.",
        required=False,
        load_default=60,
        example=60,
    )

    creation_rules = fields.List(
        fields.Nested(
            CreationRuleAttribute,
        ),
        example=[
            {
                "folder_path": "/",
                "host_attributes": {
                    "tag_snmp_ds": "no-snmp",
                    "tag_agent": "no-agent",
                    "tag_piggyback": "piggyback",
                    "tag_address_family": "no-ip",
                },
                "delete_hosts": False,
            }
        ],
        description="The first matching rule is used. You must specify at least one rule.",
        load_default=[
            {
                "folder_path": "",
                "host_attributes": {
                    "tag_snmp_ds": "no-snmp",
                    "tag_agent": "no-agent",
                    "tag_piggyback": "piggyback",
                    "tag_address_family": "no-ip",
                },
                "delete_hosts": False,
            }
        ],
    )

    activate_changes_interval = fields.Integer(
        description="A delay in seconds can be configured here so that multiple changes can be activated in one go. This avoids frequent activation of changes in situations with frequent services changes.",
        required=False,
        example=60,
    )

    discover_on_creation = fields.Boolean(
        required=False,
        load_default=True,
        description="Automatically runs a service discovery on any new hosts created by this connection. This step will add any new services to the monitoring.",
        example=True,
    )

    exclude_time_ranges = fields.List(
        fields.Nested(
            TimeIntervalAttribute,
        ),
        description="This avoids automatic changes during these times so that the automatic system doesn't interfere with user activity.",
        required=False,
        example=[{"start": "11:00", "end": "13:00"}],
    )

    no_deletion_time_after_init = fields.Integer(
        description="Seconds to prevent host deletion after site startup, e.g. when booting the Checkmk server.",
        required=False,
        load_default=600,
        example=600,
    )

    max_cache_age = fields.Integer(
        description="Seconds to keep hosts when piggyback source only sends piggyback data for other hosts.",
        required=False,
        load_default=3600,
        example=3600,
    )

    validity_period = fields.Integer(
        description="Seconds to continue consider outdated piggyback data as valid",
        required=False,
        load_default=60,
        example=60,
    )


class CreateDCD(OneOfSchema):
    type_field = "connector_type"
    type_field_remove = False
    type_schemas = {
        "piggyback": CreatePiggybackDCD,
    }
