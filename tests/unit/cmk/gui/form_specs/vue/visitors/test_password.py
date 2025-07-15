#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal
from unittest.mock import ANY, patch

import pytest

from cmk.gui.form_specs.vue import get_visitor, IncomingData, RawDiskData, RawFrontendData

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
    visitor = get_visitor(Password())
    _, frontend_value = visitor.to_vue(
        RawDiskData(("cmk_postprocessed", "explicit_password", ("", password)))
    )
    assert isinstance(frontend_value, tuple)

    assert not any(password in value for value in frontend_value if isinstance(value, str))

    disk_value: PasswordOnDisk = visitor.to_disk(RawFrontendData(frontend_value))
    assert disk_value[2][1] == password


@patch("cmk.gui.form_specs.vue.visitors.password.passwordstore_choices", return_value=[])
@pytest.mark.parametrize(
    "value",
    [
        RawDiskData(("cmk_postprocessed", "explicit_password", ("", "some_password"))),
        RawFrontendData(("explicit_password", "", "some_password", False)),
    ],
)
def test_password_masks_password(
    patch_pwstore: None, request_context: None, value: IncomingData
) -> None:
    visitor = get_visitor(Password())
    _, _, (_, masked_password) = visitor.mask(value)

    assert masked_password == "******"


@patch("cmk.gui.form_specs.vue.visitors.password.passwordstore_choices", return_value=[])
@pytest.mark.parametrize(
    ["old", "new"],
    [
        pytest.param(
            RawDiskData(("password", "secret-password")),
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
            RawDiskData(("store", "password_1")),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="migrate stored password",
        ),
        pytest.param(
            RawDiskData(("explicit_password", "067408f0-d390-4dcc-ae3c-966f278ace7d", "abc")),
            (
                "cmk_postprocessed",
                "explicit_password",
                ("067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            id="old 3-tuple explicit password",
        ),
        pytest.param(
            RawDiskData(("stored_password", "password_1", "")),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="old 3-tuple stored password",
        ),
        pytest.param(
            RawDiskData(
                (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
                )
            ),
            (
                "cmk_postprocessed",
                "explicit_password",
                ("067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            id="already migrated explicit password",
        ),
        pytest.param(
            RawDiskData(("cmk_postprocessed", "stored_password", ("password_1", ""))),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="already migrated stored password",
        ),
    ],
)
def test_password_migrates_password_on_disk(
    patch_pwstore: None,
    request_context: None,
    old: IncomingData,
    new: PasswordOnDisk,
) -> None:
    disk_visitor = get_visitor(Password(migrate=migrate_to_password))
    disk_visitor_password = disk_visitor.to_disk(old)
    assert new == disk_visitor_password
