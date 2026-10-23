#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.gui.form_specs import get_visitor, RawFrontendData, VisitorOptions
from cmk.gui.openapi.api_endpoints.models.form_spec import FormSpecValidationErrorsModel
from cmk.gui.openapi.framework.model import json_dump_without_omitted
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, Integer
from cmk.rulesets.v1.form_specs.validators import NumberInRange


def _messages_of(value: object) -> list[dict[str, object]]:
    """Convert the messages a real visitor produces and return them as serialized JSON."""
    spec = Dictionary(
        title=Title("a setting"),
        elements={
            "retries": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("retries"),
                    custom_validate=(NumberInRange(min_value=0),),
                ),
            )
        },
    )
    visitor = get_visitor(spec, VisitorOptions(migrate_values=False, mask_values=False))
    messages = visitor.validate(RawFrontendData(value))
    assert messages, "the value under test should have been rejected"

    model = FormSpecValidationErrorsModel.from_messages(messages)
    dumped: dict[str, list[dict[str, object]]] = json.loads(
        json_dump_without_omitted(FormSpecValidationErrorsModel, model)
    )
    return dumped["validation_errors"]


def test_nested_location_is_preserved() -> None:
    assert [message["location"] for message in _messages_of({"retries": -1})] == [["retries"]]


def test_every_message_has_the_form_spec_fields() -> None:
    for message in _messages_of({"retries": -1}):
        assert set(message) == {"location", "message", "replacement_value"}
        assert isinstance(message["message"], str)
