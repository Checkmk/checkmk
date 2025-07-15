#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.gui import key_mgmt
from cmk.gui.type_defs import Key

from cmk.crypto.password import Password


@pytest.mark.usefixtures("request_context")
def test_key_mgmt_create_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(time, "time", lambda: 123)

    key = key_mgmt.generate_key(
        "älias", Password("passphra$e"), UserId("dingdöng"), SiteId("test-site"), key_size=1024
    )
    assert isinstance(key, Key)
    assert key.alias == "älias"
    assert key.date == 123
    assert key.owner == "dingdöng"
    assert key.certificate.startswith("-----BEGIN CERTIFICATE---")
    assert key.private_key.startswith("-----BEGIN ENCRYPTED PRIVATE KEY---")
