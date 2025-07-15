#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.private import (
    SingleChoiceEditable,
)
from cmk.gui.form_specs.vue import get_visitor, RawFrontendData
from cmk.shared_typing.configuration_entity import ConfigEntityType


def test_single_choice_editable() -> None:
    spec = SingleChoiceEditable(
        entity_type=ConfigEntityType.notification_parameter,
        entity_type_specifier="mail",
    )

    visitor = get_visitor(spec)

    assert visitor.validate(RawFrontendData("foo")) == []
    assert visitor.to_vue(RawFrontendData("foo"))[1] == "foo"


def test_single_choice_editable_none_complains_nicely() -> None:
    spec = SingleChoiceEditable(
        entity_type=ConfigEntityType.notification_parameter,
        entity_type_specifier="mail",
    )
    visitor = get_visitor(spec)

    validation = visitor.validate(RawFrontendData(None))

    assert len(validation) == 1
    assert validation[0].message.startswith("Please choose parameters")
