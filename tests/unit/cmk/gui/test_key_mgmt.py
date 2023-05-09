#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import cmk.gui.config as config
import cmk.gui.key_mgmt as key_mgmt


def test_key_mgmt_create_key(module_wide_request_context, monkeypatch):
    monkeypatch.setattr(config.user, "id", "dingdöng")
    monkeypatch.setattr(time, "time", lambda: 123)

    key_dict = key_mgmt.PageEditKey()._generate_key("älias", "passphra$e")
    assert isinstance(key_dict, dict)
    assert sorted(key_dict.keys()) == ["alias", "certificate", "date", "owner", "private_key"]
    assert isinstance(key_dict["alias"], str)
    assert key_dict["alias"] == "älias"

    assert key_dict["date"] == 123

    assert isinstance(key_dict["owner"], str)
    assert key_dict["owner"] == "dingdöng"

    assert key_dict["certificate"].startswith("-----BEGIN CERTIFICATE---")
    assert key_dict["private_key"].startswith("-----BEGIN ENCRYPTED PRIVATE KEY---")
