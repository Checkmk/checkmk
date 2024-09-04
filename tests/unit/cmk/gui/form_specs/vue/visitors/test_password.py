#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal
from unittest.mock import patch

from cmk.utils.user import UserId

from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

from cmk.rulesets.v1.form_specs import Password

PasswordOnDisk = tuple[
    Literal["cmk_postprocessed"],
    Literal["explicit_password", "stored_password"],
    tuple[str, str],
]


@patch("cmk.gui.form_specs.vue.visitors.password.passwordstore_choices", return_value=[])
def test_password_encrypts_password(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
) -> None:
    password = "some_password"
    disk_visitor = get_visitor(Password(), VisitorOptions(data_origin=DataOrigin.DISK))
    _, frontend_value = disk_visitor.to_vue(
        ("cmk_postprocessed", "explicit_password", ("", password))
    )

    assert not any(password in value for value in frontend_value if isinstance(value, str))

    frontend_visitor = get_visitor(Password(), VisitorOptions(data_origin=DataOrigin.FRONTEND))
    disk_value: PasswordOnDisk = frontend_visitor.to_disk(frontend_value)
    assert disk_value[2][1] == password
