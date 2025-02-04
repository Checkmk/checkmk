#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal
from unittest.mock import ANY, patch

import pytest

from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

from cmk.rulesets.v1.form_specs import migrate_to_password, Password

PasswordOnDisk = tuple[
    Literal["cmk_postprocessed"],
    Literal["explicit_password", "stored_password"],
    tuple[str, str],
]


@patch("cmk.gui.form_specs.vue.visitors.password.passwordstore_choices", return_value=[])
def test_password_encrypts_password(
    patch_pwstore: None,
    request_context: None,
) -> None:
    password = "some_password"
    disk_visitor = get_visitor(Password(), VisitorOptions(data_origin=DataOrigin.DISK))
    _, frontend_value = disk_visitor.to_vue(
        ("cmk_postprocessed", "explicit_password", ("", password))
    )
    assert isinstance(frontend_value, tuple)

    assert not any(password in value for value in frontend_value if isinstance(value, str))

    frontend_visitor = get_visitor(Password(), VisitorOptions(data_origin=DataOrigin.FRONTEND))
    disk_value: PasswordOnDisk = frontend_visitor.to_disk(frontend_value)
    assert disk_value[2][1] == password


@patch("cmk.gui.form_specs.vue.visitors.password.passwordstore_choices", return_value=[])
@pytest.mark.parametrize(
    ["data_origin", "value"],
    [
        [DataOrigin.DISK, ("cmk_postprocessed", "explicit_password", ("", "some_password"))],
        [DataOrigin.FRONTEND, ("explicit_password", "", "some_password", False)],
    ],
)
def test_password_masks_password(
    patch_pwstore: None, request_context: None, data_origin: DataOrigin, value: object
) -> None:
    visitor = get_visitor(Password(), VisitorOptions(data_origin=data_origin))
    _, _, (_, masked_password) = visitor.mask(value)

    assert masked_password == "******"


@patch("cmk.gui.form_specs.vue.visitors.password.passwordstore_choices", return_value=[])
@pytest.mark.parametrize(
    ["old", "new"],
    [
        pytest.param(
            ("password", "secret-password"),
            (
                "cmk_postprocessed",
                "explicit_password",
                (
                    ANY,
                    "secret-password",
                ),
            ),
            id="migrate explicit password",
        ),
        pytest.param(
            ("store", "password_1"),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="migrate stored password",
        ),
        pytest.param(
            ("explicit_password", "067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            (
                "cmk_postprocessed",
                "explicit_password",
                ("067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            id="old 3-tuple explicit password",
        ),
        pytest.param(
            ("stored_password", "password_1", ""),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="old 3-tuple stored password",
        ),
        pytest.param(
            (
                "cmk_postprocessed",
                "explicit_password",
                ("067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            (
                "cmk_postprocessed",
                "explicit_password",
                ("067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            id="already migrated explicit password",
        ),
        pytest.param(
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="already migrated stored password",
        ),
    ],
)
def test_password_migrates_password_on_disk(
    patch_pwstore: None,
    request_context: None,
    old: object,
    new: PasswordOnDisk,
) -> None:
    disk_visitor = get_visitor(
        Password(migrate=migrate_to_password), VisitorOptions(data_origin=DataOrigin.DISK)
    )
    disk_visitor_password = disk_visitor.to_disk(old)
    assert new == disk_visitor_password
