#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict

from cmk.gui.form_specs.vue.visitors import get_visitor, RawDiskData, SingleChoiceVisitor

from cmk.rulesets.v1.form_specs import HostState


def test_host_state_recompose() -> None:
    visitor = get_visitor(HostState())
    value = RawDiskData(0)

    validation = visitor.validate(value)
    spec, frontend_value = visitor.to_vue(value)

    assert validation == []
    assert frontend_value == SingleChoiceVisitor.option_id(0)
    spec_dict = asdict(spec)
    assert spec_dict["elements"] == [
        {"name": SingleChoiceVisitor.option_id(0), "title": "UP"},
        {"name": SingleChoiceVisitor.option_id(1), "title": "DOWN"},
        {"name": SingleChoiceVisitor.option_id(2), "title": "UNREACHABLE"},
    ]
    assert spec_dict["type"] == "single_choice"
