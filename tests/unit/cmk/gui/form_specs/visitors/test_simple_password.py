#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64

import pytest

from cmk.ccc.user import UserId
from cmk.gui.form_specs import get_visitor, RawDiskData, RawFrontendData, VisitorOptions
from cmk.gui.form_specs.unstable.legacy_converter import SimplePassword
from cmk.gui.utils.encrypter import Encrypter


def test_simple_password_encrypts_disk_password(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
) -> None:
    password = RawDiskData("some_password")
    pw_visitor = get_visitor(
        SimplePassword(), VisitorOptions(migrate_values=True, mask_values=False)
    )
    _, frontend_value = pw_visitor.to_vue(password)

    assert isinstance(frontend_value, tuple)
    assert len(frontend_value) == 2
    assert isinstance(frontend_value[0], str)

    assert frontend_value[1], "Password is encrypted"
    assert frontend_value[0] != password.value


@pytest.mark.parametrize(
    "value",
    [
        RawDiskData("some_password"),
        RawFrontendData(["some_password", False]),
    ],
)
def test_simple_password_masks_password(value: RawDiskData | RawFrontendData) -> None:
    visitor = get_visitor(SimplePassword(), VisitorOptions(migrate_values=True, mask_values=True))
    password = visitor.to_disk(value)

    assert password == "******"


@pytest.mark.parametrize(
    "password",
    [
        ["some_password", False],
        [
            "test_password",
            True,
        ],
    ],
)
def test_simple_password_encrypts_frontend_password(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    password: tuple[str, bool],
) -> None:
    password_value = list(password)
    if password[1]:
        password_value[0] = base64.b64encode(Encrypter.encrypt(password[0])).decode("ascii")

    pw_visitor = get_visitor(
        SimplePassword(), VisitorOptions(migrate_values=True, mask_values=False)
    )
    _, frontend_value = pw_visitor.to_vue(RawFrontendData(password_value))

    assert isinstance(frontend_value, tuple)
    assert len(frontend_value) == 2
    assert isinstance(frontend_value[0], str)
    if not frontend_value[1]:
        raise Exception("Password is not encrypted")
    assert frontend_value[0] != password[0]
