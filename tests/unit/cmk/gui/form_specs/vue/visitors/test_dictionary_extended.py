#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.private import DictionaryExtended
from cmk.gui.form_specs.vue.visitors import DataOrigin, DEFAULT_VALUE, get_visitor, VisitorOptions

from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, String


def test_default_checked_dictionary() -> None:
    dictionary = DictionaryExtended(
        elements={"foo": DictElement(parameter_form=String(prefill=DefaultValue("bar")))},
        default_checked=["foo"],
    )
    visitor = get_visitor(dictionary, VisitorOptions(data_origin=DataOrigin.FRONTEND))

    assert visitor.to_vue({})[1] == {}
    assert visitor.to_vue(DEFAULT_VALUE)[1] == {"foo": "bar"}
