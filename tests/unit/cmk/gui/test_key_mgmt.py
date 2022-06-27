#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path

import pytest

from livestatus import SiteId

from cmk.utils.type_defs import UserId

import cmk.gui.key_mgmt as key_mgmt


@pytest.mark.usefixtures("request_context")
def test_key_mgmt_create_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(time, "time", lambda: 123)

    key = key_mgmt.generate_key("älias", "passphra$e", UserId("dingdöng"), SiteId("test-site"))
    assert isinstance(key, key_mgmt.Key)
    assert key.alias == "älias"
    assert key.date == 123
    assert key.owner == "dingdöng"
    assert key.certificate.startswith("-----BEGIN CERTIFICATE---")
    assert key.private_key.startswith("-----BEGIN ENCRYPTED PRIVATE KEY---")
