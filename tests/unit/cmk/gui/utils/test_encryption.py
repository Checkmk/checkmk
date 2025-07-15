#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pytest_mock import MockerFixture

from cmk.crypto.secrets import Secret
from cmk.gui.utils.encrypter import Encrypter


def test_value_encrypter_transparent(mocker: MockerFixture) -> None:
    mocker.patch("cmk.gui.utils.encrypter.Encrypter._get_secret", return_value=Secret(b"A" * 32))
    assert Encrypter.decrypt(Encrypter.encrypt(data := "abc")) == data
