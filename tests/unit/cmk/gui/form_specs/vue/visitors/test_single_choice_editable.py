#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.private import (
    SingleChoiceEditable,
)
from cmk.gui.form_specs.vue.visitors import get_visitor, RawFrontendData

from cmk.shared_typing.configuration_entity import ConfigEntityType


def test_single_choice_editable() -> None:
    dictionary = SingleChoiceEditable(
        entity_type=ConfigEntityType.notification_parameter,
        entity_type_specifier="mail",
    )

    visitor = get_visitor(dictionary)

    assert visitor.validate(RawFrontendData("foo")) == []
    assert visitor.to_vue(RawFrontendData("foo"))[1] == "foo"
