#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict

from cmk.gui.form_specs.vue import get_visitor, RawDiskData
from cmk.gui.form_specs.vue.visitors import SingleChoiceVisitor
from cmk.rulesets.v1.form_specs import ServiceState
from cmk.shared_typing.vue_formspec_components import SingleChoice


def test_host_state_recompose() -> None:
    visitor = get_visitor(ServiceState())
    schema, data = visitor.to_vue(RawDiskData(0))
    assert data == SingleChoiceVisitor.option_id(0)
    assert isinstance(schema, SingleChoice)
    assert asdict(schema)["elements"] == [
        {"name": SingleChoiceVisitor.option_id(0), "title": "OK"},
        {"name": SingleChoiceVisitor.option_id(1), "title": "WARN"},
        {"name": SingleChoiceVisitor.option_id(2), "title": "CRIT"},
        {"name": SingleChoiceVisitor.option_id(3), "title": "UNKNOWN"},
    ]
