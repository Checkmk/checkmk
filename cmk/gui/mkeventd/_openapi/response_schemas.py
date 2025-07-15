#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import get_args

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.fields import SiteField, Timestamp
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.livestatus_utils.commands.event_console import ServiceLevelType
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection

from cmk import fields

from .common_fields import HostNameField, PhaseField, StateField


class ECEventAttributes(BaseSchema):
    site_id = SiteField(
        description="The site id of the EC event.",
        example="heute",
        presence="should_exist",
        required=True,
    )
    state = StateField(
        required=True,
    )
    service_level = fields.String(
        enum=list(get_args(ServiceLevelType)),
        required=True,
        example="gold",
        description="The service level for this event.",
    )
    host = HostNameField(
        required=True,
    )
    rule_id = fields.String(
        required=True,
        example="rule_1",
        description="The ID of the rule.",
    )
    application = fields.String(
        required=True,
        example="app_1",
        description="The syslog tag/application this event originated from.",
    )
    comment = fields.String(
        required=True,
        example="Example comment",
        description="The event comment.",
    )
    contact = fields.String(
        required=True,
        example="Mr Monitor",
        description="The event contact information.",
    )
    ipaddress = fields.String(
        required=True,
        example="127.0.0.1",
        description="The IP address where the event originated.",
    )
    facility = fields.String(
        enum=list(ec.SyslogFacility.NAMES.values()),
        required=True,
        example="kern",
        description="The syslog facility.",
    )
    priority = fields.String(
        enum=list(ec.SyslogPriority.NAMES.values()),
        required=True,
        example="warning",
        description="The syslog priority.",
    )
    phase = PhaseField(
        required=True,
    )

    last = Timestamp(
        required=True,
        example="2017-11-09T17:32:28Z",
    )
    first = Timestamp(
        required=True,
        example="2022-11-09T16:12:12Z",
    )
    count = fields.Integer(
        required=True,
        example=1,
        description="The number of occurrences of this event within a period.",
    )
    text = fields.String(
        required=True,
        example="Sample message text",
        description="The event message text",
    )


class ECEventResponse(DomainObject):
    domainType = fields.Constant(
        "event_console",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        ECEventAttributes,
        description="The configuration attributes of a site.",
        example={
            "state": "okay",
            "service_level": "gold",
            "host": "host_1",
            "rule_id": "rule_1",
            "application": "app_1",
            "comment": "example_comment",
            "contact": "Mr Monitor",
            "ipaddress": "127.0.0.1",
            "facility": "kern",
            "priority": "warning",
            "phase": "open",
            "last": "Oct 21 2022 09:11:12",
            "first": "Oct 26 2022 07:51:25",
            "count": 1,
            "text": "Sample message text.",
        },
    )


class EventConsoleResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "event_console",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(ECEventResponse),
        description="A list of site configuration objects.",
        example=[
            {
                "links": [],
                "domainType": "event_console",
                "id": "1",
                "title": "Sample message text",
                "members": {},
                "extensions": {
                    "state": "okay",
                    "service_level": "gold",
                    "host": "host_1",
                    "rule_id": "rule_1",
                    "application": "app_1",
                    "comment": "example_comment",
                    "contact": "Mr Monitor",
                    "ipaddress": "127.0.0.1",
                    "facility": "kern",
                    "priority": "warning",
                    "phase": "open",
                    "last": "Oct 21 2022 09:11:12",
                    "first": "Oct 26 2022 07:51:25",
                    "count": 1,
                    "text": "Sample message text",
                },
            }
        ],
    )
