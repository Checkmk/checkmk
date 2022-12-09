#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from marshmallow import post_load, ValidationError
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.livestatus_helpers.tables.eventconsoleevents import Eventconsoleevents

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.plugins.openapi.endpoints.event_console.common_fields import (
    ApplicationField,
    HostNameField,
    PhaseField,
    StateField,
)

from cmk import fields


class FilterParams(BaseSchema):
    state = StateField(
        required=False,
    )
    host = HostNameField(
        required=False,
    )
    phase = PhaseField(
        required=False,
    )
    application = ApplicationField(
        required=False,
    )

    @post_load
    def verify_at_least_one(self, *args, **kwargs):
        at_least_one_of = {"state", "host", "application", "phase"}
        if not at_least_one_of & set(args[0]):
            raise ValidationError(
                f"At least one of the following parameters should be provided: {at_least_one_of}"
            )
        return args[0]


class FilterParamsUpdateAndAcknowledge(BaseSchema):
    state = StateField(
        required=False,
    )
    host = HostNameField(
        required=False,
    )
    application = ApplicationField(
        required=False,
    )

    @post_load
    def verify_at_least_one(self, *args, **kwargs):
        at_least_one_of = {"state", "host", "application"}
        if not at_least_one_of & set(args[0]):
            raise ValidationError(
                f"At least one of the following parameters should be provided: {at_least_one_of}"
            )
        return args[0]


ec_query = gui_fields.query_field(
    Eventconsoleevents,
    required=True,
    example='{"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}',
)

ec_filters = fields.Nested(
    FilterParams,
    required=True,
)


class DeleteFilterBase(BaseSchema):
    filter_type = fields.String(
        enum=["by_id", "query", "params"],
        required=True,
        example="by_id",
        description="The way you would like to filter events.",
    )


class FilterById(DeleteFilterBase):
    event_id = fields.Integer(
        required=True,
        description="The event console ID",
        example=1,
    )


class FilterByQuery(DeleteFilterBase):
    query = ec_query


class FilterByParams(DeleteFilterBase):
    filters = ec_filters


class DeleteECEvents(OneOfSchema):
    type_field = "filter_type"
    type_field_remove = False
    type_schemas = {
        "by_id": FilterById,
        "query": FilterByQuery,
        "params": FilterByParams,
    }


class ChangeEventState(BaseSchema):
    new_state = StateField(
        required=True,
    )


class ChangeStateFilter(ChangeEventState):
    filter_type = fields.String(
        enum=["query", "params"],
        required=True,
        example="params",
        description="The way you would like to filter events.",
    )


class ChangeStateWithQuery(ChangeStateFilter):
    query = ec_query


class ChangeStateWithParams(ChangeStateFilter):
    filters = ec_filters


class ChangeEventStateSelector(OneOfSchema):
    type_field = "filter_type"
    type_field_remove = False
    type_schemas = {
        "query": ChangeStateWithQuery,
        "params": ChangeStateWithParams,
    }


class UpdateAndAcknowledgeEvent(BaseSchema):
    change_comment = fields.String(
        required=False,
        example="Comment now acked",
        description="Event comment.",
    )
    change_contact = fields.String(
        required=False,
        example="Mr Monitor",
        description="Contact information.",
    )


class UpdateAndAcknowledgeFilter(UpdateAndAcknowledgeEvent):
    filter_type = fields.String(
        enum=["query", "params"],
        required=True,
        example="by_id",
        description="The way you would like to filter events.",
    )


class UpdateAndAcknowledgeWithQuery(UpdateAndAcknowledgeFilter):
    query = ec_query


class UpdateAndAcknowledgeWithParams(UpdateAndAcknowledgeFilter):
    filters = fields.Nested(
        FilterParamsUpdateAndAcknowledge,
        required=True,
    )


class UpdateAndAcknowledgeSelector(OneOfSchema):
    type_field = "filter_type"
    type_field_remove = False
    type_schemas = {
        "query": UpdateAndAcknowledgeWithQuery,
        "params": UpdateAndAcknowledgeWithParams,
    }
