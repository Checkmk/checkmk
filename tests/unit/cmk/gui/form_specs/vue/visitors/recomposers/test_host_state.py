#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict

from cmk.ccc.user import UserId

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.visitors import SingleChoiceVisitor
from cmk.gui.form_specs.vue.visitors._type_defs import DataOrigin
from cmk.gui.session import UserContext

from cmk.rulesets.v1.form_specs import HostState


def test_host_state_recompose(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
) -> None:
    with UserContext(with_user[0]):
        vue_app_config = serialize_data_for_frontend(
            HostState(),
            "ut_id",
            DataOrigin.DISK,
            do_validate=True,
            value=0,
        )

        data = asdict(vue_app_config.spec)
        assert data["elements"] == [
            {"name": SingleChoiceVisitor.option_id(0), "title": "UP"},
            {"name": SingleChoiceVisitor.option_id(1), "title": "DOWN"},
            {"name": SingleChoiceVisitor.option_id(2), "title": "UNREACHABLE"},
        ]
        assert data["type"] == "single_choice"
