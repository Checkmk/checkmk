#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The FormSpec dialogs the SPA renders, and the translation of their values.

Serialising a FormSpec needs the GUI request and the authenticated user (a
``Password`` field lists that user's password store), which the Maps daemon
cannot provide — so it happens in the GUI process, here. The work itself lives
in :mod:`cmk.maps.gui._form_schemas`.

Both are POSTs although the first is a read: the value bag is structured and
unbounded, so it belongs in a body rather than a query string — the same reason
the aggregation lookups take one.
"""

from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.maps.gui._form_schemas import FormSchemaName, parse_form_values, render_form_schema
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.request_models import MapsFormValuesRequest
from cmk.maps.rest_api.internal.models.response_models import (
    MapsFormParseResponse,
    MapsFormSchemaResponse,
    MapsValidationMessage,
)
from cmk.maps.rest_api.utils import NO_CONFIG_CHANGE
from cmk.web.utils import permission_verification as permissions

_SpecName = Annotated[
    FormSchemaName,
    PathParam(description="The dialog to render.", example="map_metadata"),
]


def show_form_schema_v1(spec: _SpecName, body: MapsFormValuesRequest) -> MapsFormSchemaResponse:
    """Show a Maps dialog's form spec, with its values"""
    user.need_permission("maps.use")
    schema, data = render_form_schema(spec, ApiOmitted.to_optional(body.data))
    return MapsFormSchemaResponse(schema_=schema, data=data)


def parse_form_v1(spec: _SpecName, body: MapsFormValuesRequest) -> MapsFormParseResponse:
    """Translate a Maps dialog's edited values into their stored form"""
    user.need_permission("maps.use")
    values = ApiOmitted.to_optional(body.data) or {}
    parsed, messages = parse_form_values(spec, values)
    if parsed is None:
        return MapsFormParseResponse(
            validation=[
                MapsValidationMessage(
                    location=list(message.location),
                    message=message.message,
                    replacement_value=message.replacement_value,
                )
                for message in messages
            ]
        )
    return MapsFormParseResponse(data=parsed)


ENDPOINT_SHOW_FORM_SCHEMA = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("maps_form", "{spec}", "schema"),
        link_relation="cmk/show_maps_form_schema",
        method="post",
    ),
    permissions=EndpointPermissions(required=permissions.Perm("maps.use")),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_form_schema_v1)},
)

ENDPOINT_PARSE_FORM = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("maps_form", "{spec}", "parse"),
        link_relation="cmk/parse_maps_form",
        method="post",
    ),
    permissions=EndpointPermissions(required=permissions.Perm("maps.use")),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=parse_form_v1)},
)
