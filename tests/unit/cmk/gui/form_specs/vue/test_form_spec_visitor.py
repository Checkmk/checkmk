#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.type_defs import DataOrigin

from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, String


def test_dictionary_visitor_only_fills_required_prefill():
    form_spec = Dictionary(
        elements={
            "required_el": DictElement(
                parameter_form=String(
                    prefill=DefaultValue("el1_prefill"),
                ),
                required=True,
            ),
            "optional_el": DictElement(
                parameter_form=String(
                    prefill=DefaultValue("el2_prefill"),
                ),
            ),
        },
    )

    vue_app_config = serialize_data_for_frontend(
        form_spec, "foo_field_id", DataOrigin.DISK, do_validate=False
    )

    assert vue_app_config.data == {
        "required_el": "el1_prefill",
    }
