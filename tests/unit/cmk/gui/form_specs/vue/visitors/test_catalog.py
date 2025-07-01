#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.user import UserId

from cmk.gui.form_specs.private import Catalog, Topic, TopicElement
from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import String
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.shared_typing.vue_formspec_components import ValidationMessage


def test_catalog_validation_simple(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
) -> None:
    spec = Catalog(
        elements={
            "some_key": Topic(
                title=Title("some_key title"),
                elements={
                    "key": TopicElement(
                        parameter_form=String(custom_validate=[LengthInRange(5, None)])
                    )
                },
            )
        }
    )
    visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.DISK))

    validation_messages = visitor.validate({"some_key": {"key": "string"}})
    assert validation_messages == []

    validation_messages = visitor.validate({"some_key": {"key": ""}})
    assert validation_messages == [
        ValidationMessage(
            location=[
                "some_key",
                "key",
            ],
            message="The minimum allowed length is 5.",
            replacement_value="",
        )
    ]


def test_catalog_serializes_empty_topics_to_disk() -> None:
    spec = Catalog(
        elements={
            "some_topic": Topic(
                title=Title("some_key title"),
                elements={
                    "key": TopicElement(
                        parameter_form=String(custom_validate=[LengthInRange(5, None)])
                    )
                },
            )
        }
    )
    visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.DISK))

    disk_data = visitor.to_disk({"some_topic": {}})

    assert disk_data == {"some_topic": {}}
