#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection

from cmk import fields


class ConnectedSiteAttributes(BaseSchema):
    site_id = fields.String(
        required=True,
        description="The site id.",
        example="heute_remote_1",
    )


class BrokerConnectionExtension(BaseSchema):
    id = fields.String(description="The unique identifier of the connection.")
    connecter = fields.Nested(
        ConnectedSiteAttributes,
        description="The attributes of the site initiating the connection.",
        example={"site_id": "heute_remote_1"},
    )
    connectee = fields.Nested(
        ConnectedSiteAttributes,
        description="The attributes of the site accepting the connection.",
        example={"site_id": "heute_remote_2"},
    )


class BrokerConnectionResponse(DomainObject):
    domainType = fields.Constant(
        "broker_connection",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        BrokerConnectionExtension,
        description="The configuration attributes of a broker peer to peer connection.",
        example={
            "domainType": "broker_connection",
            "id": "connection_1",
            "connecter": {"site_id": "heute_remote_1"},
            "connectee": {"site_id": "heute_remote_2"},
        },
    )


class BrokerConnectionResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "broker_connection",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(BrokerConnectionResponse),
        description="A list of broker peer to peer configuration objects.",
        example=[
            {
                "domainType": "broker_connection",
                "id": "connection_1",
                "connecter": {"site_id": "heute_remote_1"},
                "connectee": {"site_id": "heute_remote_2"},
            }
        ],
    )
