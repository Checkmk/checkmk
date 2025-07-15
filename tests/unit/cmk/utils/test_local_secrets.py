#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId

from cmk.utils.local_secrets import AutomationUserSecret


def test_automation_user_secret(patch_omd_site: None) -> None:
    aus = AutomationUserSecret(UserId("crypto_secrets_new_user"))

    assert not aus.exists()
    with pytest.raises(FileNotFoundError):
        aus.read()

    aus.path.parent.mkdir()  # profile dir of the test user
    aus.save(secret := "this is a test 🤡")

    assert aus.exists()
    assert aus.read() == secret

    assert not aus.check("")
    assert not aus.check("wrong")
    assert aus.check(secret)
