#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from typing import Literal

import pytest
from pytest import MonkeyPatch

from cmk.gui.wato._notification_parameter._ilert import _migrate_to_password
from cmk.utils import password_store


@pytest.mark.parametrize(
    "old_pwd, new_pwd",
    [
        pytest.param(
            ("ilert_api_key", "mypassword"),
            (
                "cmk_postprocessed",
                "explicit_password",
                ("uuida1111c1a-f86e-11da-bd1a-00112444be1e", "mypassword"),
            ),
            id="Explicit password",
        ),
        pytest.param(
            ("store", "password_1"),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="Stored password",
        ),
        pytest.param(
            ("cmk_postprocessed", "stored_password", ("password_2", "")),
            ("cmk_postprocessed", "stored_password", ("password_2", "")),
            id="Already migrated",
        ),
    ],
)
def test_migrate_to_password(
    old_pwd: tuple[str, str],
    new_pwd: tuple[
        Literal["cmk_postprocessed"],
        Literal["explicit_password", "stored_password"],
        tuple[str, str],
    ],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        password_store,
        "ad_hoc_password_id",
        lambda: f"uuid{uuid.UUID('a1111c1a-f86e-11da-bd1a-00112444be1e')}",
    )
    assert _migrate_to_password(old_pwd) == new_pwd
