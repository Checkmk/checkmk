#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.user import UserId

from cmk.gui.form_specs.private import Catalog, Topic
from cmk.gui.form_specs.vue.shared_type_defs import ValidationMessage
from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

from cmk.rulesets.v1.form_specs import DictElement, Dictionary, String
from cmk.rulesets.v1.form_specs.validators import LengthInRange


def test_catalog_validation_simple(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
) -> None:
    spec = Catalog(
        topics=[
            Topic(
                ident="some_key",
                dictionary=Dictionary(
                    elements={
                        "key": DictElement(
                            parameter_form=String(custom_validate=[LengthInRange(5, None)])
                        )
                    }
                ),
            )
        ]
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
            invalid_value="",
        )
    ]
