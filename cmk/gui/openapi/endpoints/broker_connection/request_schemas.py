#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from marshmallow import validates_schema, ValidationError

from cmk.gui import fields as gui_fields
from cmk.gui.fields.definitions import ConnectionIdentifier
from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class SiteId(BaseSchema):
    site_id = gui_fields.SiteField(
        presence="should_exist",
        required=True,
        description="The site ID.",
        example="prod",
    )


class BrokerConnectionConfig(BaseSchema):
    connecter = fields.Nested(
        SiteId,
        required=True,
        description="The ID of the site initiating the connection.",
        example={"site_id": "remote_1"},
    )
    connectee = fields.Nested(
        SiteId,
        required=True,
        description="The ID of the site accepting the connection.",
        example={"site_id": "remote_2"},
    )

    @validates_schema
    def validate_connection(self, data: dict[str, Any], **kwargs: Any) -> None:
        """The two connected sites should not be the same."""
        if data["connecter"]["site_id"] != data["connectee"]["site_id"]:
            return
        raise ValidationError(
            "The site initiating the connection and the site accepting the connection"
            " should not have the same ID."
        )


class BrokerConnectionRequestCreate(BaseSchema):
    connection_id = ConnectionIdentifier(
        required=True,
        presence="should_not_exist",
        description="An unique connection id for the broker connection",
        example="connection_1",
    )

    connection_config = fields.Nested(
        BrokerConnectionConfig,
        required=True,
        description="The connection configuration.",
        example={"connecter": {"site_id": "remote_1"}, "connectee": {"site_id": "remote_2"}},
    )


class BrokerConnectionRequestUpdate(BaseSchema):
    connection_config = fields.Nested(
        BrokerConnectionConfig,
        required=True,
        description="The connection configuration.",
        example={"connecter": {"site_id": "remote_1"}, "connectee": {"site_id": "remote_2"}},
    )
